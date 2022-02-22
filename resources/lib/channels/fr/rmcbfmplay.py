# -*- coding: utf-8 -*-
# Copyright: (c) 2021, sy6sy2
# GNU General Public License v2.0+ (see LICENSE.txt or https://www.gnu.org/licenses/gpl-2.0.txt)

# This file is part of Catch-up TV & More

from __future__ import unicode_literals
import xbmcaddon
import base64
import inputstreamhelper
import urlquick
import re
import json

from builtins import str
from codequick import Listitem, Resolver, Route, Script
from kodi_six import xbmcgui

from resources.lib import download, web_utils
from resources.lib.addon_utils import get_item_media_path
from resources.lib.kodi_utils import (INPUTSTREAM_PROP, get_kodi_version,
                                      get_selected_item_art,
                                      get_selected_item_info,
                                      get_selected_item_label)
from resources.lib.menu_utils import item_post_treatment

@Route.register
def get_token():
    autorization = xbmcaddon.Addon("plugin.video.catchuptvandmore").getSetting('rmcbfmplay.login') + ":" + xbmcaddon.Addon("plugin.video.catchuptvandmore").getSetting('rmcbfmplay.password')
    url = "https://sso-client.sfr.fr/cas/services/rest/3.2/createToken.json"
    params = {"duration": 86400}
    headers = {
        "secret": "Basic Uk1DQkZNUGxheUFuZHJvaWR2MTptb2ViaXVzMTk3MA==",
        "Authorization": "Basic " + base64.b64encode(autorization.encode("utf-8")).decode("utf-8"),
    }
    resp = urlquick.get(url, params=params, headers=headers).json()
    token = resp["createToken"]["token"]
    return token

def get_account_id(token):
    url = "https://ws-backendtv.rmcbfmplay.com/heimdall-core/public/api/v2/userProfiles"
    params = {
        "app": "bfmrmc",
        "device": "browser",
        "noTracking": "true",
        "token": token,
        "tokenType": "casToken",
    }
    headers = {"User-Agent": USER_AGENT}
    resp = urlquick.get(url, params=params, headers=headers).json()
    account_id = resp["nexttvId"]
    return account_id

API_BACKEND = "https://ws-backendtv.rmcbfmplay.com/gaia-core/rest/api/"
API_CDN_ROOT = "https://ws-cdn.tv.sfr.net/gaia-core/rest/api/"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:96.0) Gecko/20100101 Firefox/96.0"
token = get_token()
account_id = get_account_id(token)

@Route.register
def rmcbfmplay_root(plugin, **kwargs):
    """Root menu of the app."""
    url = API_BACKEND + "web/v1/menu/RefMenuItem::rmcgo_home/structure"
    params = {"app":"bfmrmc","device":"browser","profileId":account_id,"accountTypes":"NEXTTV","operators":"NEXTTV","noTracking":"false"}
    headers = {"User-Agent": USER_AGENT}
    resp = urlquick.get(url, params=params, headers=headers).json() 
    for spot in resp["spots"]:
        item = Listitem()
        item.label = spot["title"]
        item.set_callback(menu, "web/v1/spot/%s/content" % spot["id"])
        item_post_treatment(item)
        yield item

@Route.register
def menu(plugin, path, **kwargs):
    """Menu of the app with v1 API."""

    if "/spot/" in path or "/tile/" in path:
        url = API_BACKEND + path
        params = {"app":"bfmrmc","device":"browser","token":token,"page":"0","size":"30","profileId":account_id,"accountTypes":"NEXTTV","operators":"NEXTTV","noTracking":"false"}
    else:
        url = API_CDN_ROOT + path
        params = {"universe":"PROVIDER","accountTypes":"NEXTTV","operators":"NEXTTV","noTracking":"false"}   

    headers = {"User-Agent": USER_AGENT}
    resp = urlquick.get(url, params=params, headers=headers).json()

    if "items" in resp:
        key = "items"
    elif "spots" in resp:
        key = "spots"
    elif "content" in resp:
        key = "content"
    elif "tiles" in resp:
        key = "tiles"
    else:
        print("RESP", resp)

    for elt in resp[key]:
        types = elt.get('contentType',"")
        if types:
            #Some links allow you to launch the content directly.
            #Exemple "Haro sur les eoliennes"
            if types == "Movie" or types == "Episode":
                _id = elt["action"]["actionIds"]["contentId"]
                target_path = "web/v2/content/%s/options" % _id
                callback = (video, target_path, elt["title"])

            else:
                target_path = "web/v1/content/%s/episodes" % (
                    elt["action"]["actionIds"]["contentId"]
                )

                callback = (menu, target_path)
        else:
            # Find key 1
            if "more" in elt:
                key1 = "more"
            elif "action" in elt:
                key1 = "action"
            else:
                print("ELT1", elt)
                key1 = None

            if key1:
                if not elt[key1]["actionIds"]:
                    continue

                key2 = elt[key1]["actionIds"]
                if type(key2) is not dict:
                    subpath = key2[:-2]

                    # Find path suffix
                    suffix = elt[key1]["actionType"]

                    target_path = "web/v1/%s/%s/%s" % (
                        subpath,
                        elt[key1]["actionIds"][key2],
                        suffix,
                    )

                    callback = (menu, target_path)
                else:
                    callback = (podscast, key2["url"])                    

            else:
                _id = elt["id"]
                target_path = "web/v2/content/%s/options" % _id
                callback = (video, target_path, elt["title"])

        item = Listitem()
        item.label = elt["title"]
        if "description" in elt:
            item.info["plot"] = elt["description"]
        # TODO: castings, etc

        item.art["thumb"] = ""
        for image in elt["images"]:
            if image["format"] == "1/1" and not item.art["thumb"]:
                item.art["thumb"] = image["url"]
            elif image["format"] == "2/3":
                item.art["thumb"] = image["url"]
            elif image["format"] == "16/9":
                item.art["fanart"] = image["url"]
        item.set_callback(*callback)
        item_post_treatment(item)
        yield item


@Resolver.register
def video(plugin, path, title, **kwargs):
    """Menu of the app with v1 API."""

    # https://ws-cdn.tv.sfr.net/gaia-core/rest/api/web/v1/content/Product::NEUF_BFMTV_BFM0300012711/detail?app=bfmrmc&device=browser&page=0&size=30
    # https://ws-cdn.tv.sfr.net/gaia-core/rest/api/web/v1/content/Product::NEUF_BFMTV_BFM0300012711/detail?app=bfmrmc&device=browser&isProductSeasonWithEpisodes=false&universe=provider
    # https://ws-gaia.tv.sfr.net/gaia-core/rest/api/web/v2/content/Product::NEUF_BFMTV_BFM0300012711/options?app=bfmrmc&device=browser&noTracking=true&token=PIEOVEsvhCYGqC7df4/pvt7TiglWvZqtpW9qdSlvqAyH6bOcdj0JNJmqylF5fws2X29FA1r7isvuWGGhuXpxzGPax1g53%2BuHcPYjHs1z8hkweHk1x2USpCdykMd1wOp%2B5w74DI0c1vl50fZqpCRnR4ppMCbFYhEpThQaLPRvJHgXh7EnJ3IJeJULerWHA%2BjGc&tokenType=casToken&universe=provider
    url = API_CDN_ROOT + path
    params = {
        "app": "bfmrmc",
        "device": "browser",
        "token": token,
        "universe": "provider",
        "accountTypes":"NEXTTV",
        "operators":"NEXTTV",
        "noTracking":"false"
    }

    headers = {"User-Agent": USER_AGENT}
    resp = urlquick.get(url, params=params, headers=headers).json()

    for stream in resp[0]["offers"][0]["streams"]:
        if stream["drm"] == "WIDEVINE":
            item = Listitem()
            item.label = get_selected_item_label()
            item.art.update(get_selected_item_art())
            item.info.update(get_selected_item_info())
            item.path = stream["url"]
            item.property[INPUTSTREAM_PROP] = "inputstream.adaptive"
            item.property["inputstream.adaptive.manifest_type"] = "mpd"
            item.property["inputstream.adaptive.license_type"] = "com.widevine.alpha"
            customdata = "description={}&deviceId=byPassARTHIUS&deviceName=Firefox-96.0----Windows&deviceType=PC&osName=Windows&osVersion=10&persistent=false&resolution=1600x900&tokenType=castoken&tokenSSO={}&entitlementId=3769416154&type=LIVEOTT&accountId={}".format(
                USER_AGENT, token, account_id
            )

            import urllib.parse

            customdata = urllib.parse.quote(customdata)
            item.property["inputstream.adaptive.license_key"] = (
                "https://ws-backendtv.rmcbfmplay.com/asgard-drm-widevine/public/licence|User-Agent=" + USER_AGENT + "&customdata="
                + customdata + "&Origin=https://www.rmcbfmplay.com&Content-Type="
                + "|R{SSM}|"
            )
            return item

@Route.register
def podscast(plugin, path, **kwargs):
    headers = {"User-Agent": USER_AGENT}
    resp = urlquick.get(path, headers=headers).text

    if "bfmtv.com" in path:
        data = re.compile('margin-top">.+?<a href="(.+?)".+?name">(.+?)<.+?description">(.+?)<', re.DOTALL|re.MULTILINE).findall(resp)

        for d in data:
            item = Listitem()
            item.path = d[0]
            item.label = d[1]
            item.info["plot"] = d[2]
            item.art.update(get_selected_item_art())    

            callback = (playpodcast, item.path, item.label)
            item.set_callback(*callback)
            item_post_treatment(item)
            yield item

    elif "deezer.com" in path:
        data = re.compile('window.__DZR_APP_STATE__ =(.+?)</script', re.DOTALL|re.MULTILINE).search(resp).group(1)
        data = json.loads(data)

        for d in data["EPISODES"]["data"]:
            item = Listitem()
            item.path = d["EPISODE_DIRECT_STREAM_URL"]
            item.label = d["EPISODE_TITLE"]
            item.info["plot"] = d["EPISODE_DESCRIPTION"]
            item.art.update(get_selected_item_art())

            callback = (playpodcast, item.path, item.label)
            item.set_callback(*callback)
            item_post_treatment(item)
            yield item


@Resolver.register
def playpodcast(plugin, path, title, **kwargs):
    item = Listitem()
    item.label = title
    item.art.update(get_selected_item_art())
    item.info.update(get_selected_item_info())

    if ".mp3" in path:
        item.path = path + "|User-Agent=" + USER_AGENT + "&Referer=https://www.deezer.com/"
    else:
        headers = {"User-Agent": USER_AGENT}
        resp = urlquick.get(path, headers=headers)
        data = resp.parse()
        
        if "bfmtv.com" in path:
            item.path = data.find(".//div[@class='audio-player']").get('data-media-url')
    return item