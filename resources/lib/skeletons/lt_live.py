# -*- coding: utf-8 -*-
# Copyright: (c) 2022, Joaopa
# GNU General Public License v2.0+ (see LICENSE.txt or https://www.gnu.org/licenses/gpl-2.0.txt)

# This file is part of Catch-up TV & More

from __future__ import unicode_literals

# The following dictionaries describe
# the addon's tree architecture.
# * Key: item id
# * Value: item infos
#    - route (folder)/resolver (playable URL): Callback function to run once this item is selected
#    - thumb: Item thumb path relative to "media" folder
#    - fanart: Item fanart path relative to "media" folder

root = 'live_tv'

menu = {
    'LTV1': {
        'resolver': '/resources/lib/channels/lt/lrt:get_live_url',
        'label': 'LRT Televizija',
        'thumb': 'channels/sg/lrt.png',
        'fanart': 'channels/sg/lrt_fanart.jpg',
        'enabled': True,
        'order': 1
    },
    'LTV2': {
    'resolver': '/resources/lib/channels/lt/lrt:get_live_url',
    'label': 'LRT PLIUS',
    'thumb': 'channels/sg/lrtplius.png',
    'fanart': 'channels/sg/lrtplius_fanart.jpg',
    'enabled': True,
    'order': 1
    },
}