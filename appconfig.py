brokerSettings = {
    'address'   : '192.168.0.73',
    'port'      : 1883,
    'client'    : 'Raspy'
}

SystemSettings = {
    'pdSendPath': '/Applications/Pd-0.48-1.app/Contents/Resources/bin/pdsend',
    'otaUpdateUrl': 'http://192.168.0.164:8000/Firmware/moon_melon.bin',
}

SoundSets = {
    '../media/clio-sounds': {
        'mode': 'SINGLE_HIT',
    },
    '../media/clio-hang': {
        'mode': 'SINGLE_HIT',
    },
    '../media/clio-giusti': {
        'mode': 'SINGLE_HIT',
    },
    '../media/loops1': {
        'mode': 'LOOP',
        'duration': '4000'
    },
    '../media/luki1': {
        'mode': 'LOOP',
        'duration': '4000'
    },
    '../media/luki2': {
        'mode': 'LOOP',
        'duration': '8000'
    },
    '../media/luki3': {
        'mode': 'LOOP',
        'duration': '4000'
    },
    '../media/luki-ambient': {
        'mode': 'LOOP',
        'duration': '4000'
    },
    '../media/luki-mixed': {
        'mode': 'SINGLE_HIT',
    },
    '../media/luki-sequenced': {
        'mode': 'LOOP',
        'duration': '4000'
    },

    '../media/christian-thebeat': {
        'mode': 'LOOP',
        'duration': '14328'
    },
    '../media/christian-thepiano': {
        'mode': 'SINGLE_HIT',
    },
    '../media/christian-sinitus': {
        'mode': 'SINGLE_HIT',
    },
}
SensorNames = {
    "68:C6:3A:C3:70:E5": "A 1", "38:2B:78:05:13:61": "A 2", "38:2B:78:03:CF:5D": "A 3", "68:C6:3A:C3:00:D0": "A 4", "68:C6:3A:C3:77:40" : "A 5",
    "68:C6:3A:C3:06:63": "B 1", "B2": "B 2", "B3": "B 3", "B4": "B 4", "B5" : "B 5",
    "68:C6:3A:C3:03:A3": "C 1", "C2": "C 2", "C3": "C 3", "C4": "C 4", "C5" : "C 5",
    "D1": "D 1", "D2": "D 2", "D3": "D 3", "D4": "D 4", "D5" : "D 5",
    "E1": "E 1", "E2": "E 2", "E3": "E 3", "E4": "E 4", "E5" : "E 5"
}
Controller = {
    "steps": [
        {
            'startTime': '21:18:15',
            'mqttCommand': '',
            'pdCommand': '',
            'set': '../media/clio-sounds'
        },
        {
            'startTime': '21:18:25',
            'mqttCommand': '',
            'pdCommand': '',
            'set': '../media/loops1'
        },
        {
            'startTime': '21:42:00',
            'mqttCommand': '',
            'pdCommand': 'A 1 load ../media/set1/intro.wav, A 1 play, C 2 play, D 3 play',
            'set': '../media/clio-sounds',
            'masterVolume': 0.8,

        }
    ]
}
