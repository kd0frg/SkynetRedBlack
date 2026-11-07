var plasma = getApiVersion(1);

var layout = {
    "desktops": [
        {
            "applets": [
            ],
            "config": {
                "/": {
                    "ItemGeometries-1920x1080": "",
                    "ItemGeometriesHorizontal": "",
                    "formfactor": "0",
                    "immutability": "1",
                    "lastScreen": "0",
                    "wallpaperplugin": "org.kde.image"
                },
                "/ConfigDialog": {
                    "DialogHeight": "630",
                    "DialogWidth": "810"
                },
                "/General": {
                    "arrangement": "1"
                },
                "/Wallpaper/org.kde.image/General": {
                    "Image": "file://file://$HOME/.local/share/wallpapers/SkynetRedBlack/skynet-wallpaper.jpg",
                    "SlidePaths": "/,h,o,m,e,/,c,o,l,e,/,.,l,o,c,a,l,/,s,h,a,r,e,/,w,a,l,l,p,a,p,e,r,s,/,\\,,/,u,s,r,/,s,h,a,r,e,/,w,a,l,l,p,a,p,e,r,s,/"
                }
            },
            "wallpaperPlugin": "org.kde.image"
        },
        {
            "applets": [
            ],
            "config": {
                "/": {
                    "ItemGeometries-1920x1080": "",
                    "ItemGeometriesHorizontal": "",
                    "formfactor": "0",
                    "immutability": "1",
                    "lastScreen": "1",
                    "wallpaperplugin": "org.kde.color"
                },
                "/ConfigDialog": {
                    "DialogHeight": "630",
                    "DialogWidth": "810"
                },
                "/Wallpaper/org.kde.color/General": {
                    "Color": "0,0,0"
                }
            },
            "wallpaperPlugin": "org.kde.color"
        }
    ],
    "panels": [
        {
            "alignment": "left",
            "applets": [
                {
                    "config": {
                        "/": {
                            "popupHeight": "580",
                            "popupWidth": "683"
                        },
                        "/ConfigDialog": {
                            "DialogHeight": "630",
                            "DialogWidth": "810"
                        },
                        "/General": {
                            "alphaSort": "true",
                            "compactMode": "true",
                            "favoritesPortedToKAstats": "true",
                            "systemFavorites": "suspend\\,hibernate\\,reboot\\,shutdown"
                        }
                    },
                    "plugin": "org.kde.plasma.kickoff"
                },
                {
                    "config": {
                    },
                    "plugin": "org.kde.plasma.pager"
                },
                {
                    "config": {
                        "/General": {
                            "launchers": "applications:systemsettings.desktop,preferred://filemanager,preferred://browser,applications:org.kde.konsole.desktop"
                        }
                    },
                    "plugin": "org.kde.plasma.icontasks"
                },
                {
                    "config": {
                    },
                    "plugin": "org.kde.plasma.marginsseparator"
                },
                {
                    "config": {
                    },
                    "plugin": "org.kde.plasma.systemtray"
                },
                {
                    "config": {
                        "/": {
                            "popupHeight": "400",
                            "popupWidth": "560"
                        },
                        "/Appearance": {
                            "fontFamily": "Noto Sans",
                            "fontWeight": "400",
                            "showSeconds": "Always"
                        },
                        "/ConfigDialog": {
                            "DialogHeight": "630",
                            "DialogWidth": "810"
                        }
                    },
                    "plugin": "org.kde.plasma.digitalclock"
                },
                {
                    "config": {
                    },
                    "plugin": "org.kde.plasma.showdesktop"
                },
                {
                    "config": {
                        "/": {
                            "CurrentPreset": "org.kde.plasma.systemmonitor",
                            "popupHeight": "385",
                            "popupWidth": "256"
                        },
                        "/Appearance": {
                            "chartFace": "org.kde.ksysguard.piechart"
                        },
                        "/ConfigDialog": {
                            "DialogHeight": "630",
                            "DialogWidth": "810"
                        },
                        "/SensorColors": {
                            "cpu/all/usage": "85,0,0",
                            "gpu/gpu0/coreFrequency": "85,0,0",
                            "gpu/gpu0/power": "255,0,0",
                            "gpu/gpu0/temperature": "170,45,7",
                            "gpu/gpu0/usage": "0,0,0",
                            "gpu/gpu0/usedVram": "53,0,0",
                            "memory/physical/free": "255,0,0",
                            "memory/physical/total": "170,0,0",
                            "memory/physical/used": "85,0,0"
                        },
                        "/SensorLabels": {
                            "gpu/gpu0/coreFrequency": "RTX 5070 Freq",
                            "gpu/gpu0/power": "RTX 5070 Power",
                            "gpu/gpu0/temperature": "RTX 5070 Temp",
                            "gpu/gpu0/usage": "RTX 5070] Usage",
                            "gpu/gpu0/usedVram": "RTX 5070 Mem Used"
                        },
                        "/Sensors": {
                            "highPrioritySensorIds": "[\"cpu/all/usage\",\"memory/physical/total\",\"memory/physical/used\",\"memory/physical/free\",\"gpu/gpu0/temperature\",\"gpu/gpu0/coreFrequency\",\"gpu/gpu0/usedVram\",\"gpu/gpu0/power\",\"gpu/gpu0/temperature\",\"gpu/gpu0/usage\"]",
                            "totalSensors": "[\"cpu/all/maximumFrequency\",\"lmsensors/zenpower-pci-00c3/temp1\"]"
                        }
                    },
                    "plugin": "org.kde.plasma.systemmonitor"
                },
                {
                    "config": {
                    },
                    "plugin": "org.kde.plasma.trash"
                }
            ],
            "config": {
                "/": {
                    "formfactor": "2",
                    "immutability": "1",
                    "lastScreen": "0",
                    "wallpaperplugin": "org.kde.image"
                }
            },
            "floating": false,
            "floatingApplets": false,
            "height": 3.7777777777777777,
            "hiding": "normal",
            "lengthMode": "fill",
            "location": "bottom",
            "maximumLength": 106.66666666666667,
            "minimumLength": 106.66666666666667,
            "offset": 0,
            "opacity": "translucent"
        }
    ],
    "serializationFormatVersion": "1"
}
;

plasma.loadSerializedLayout(layout);
