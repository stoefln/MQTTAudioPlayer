brokerSettings = {
    'address'   : '192.168.0.73',
    'port'      : 1883,
    'topic'     : 'sensor', 
    'client'    : 'Raspy'}

SystemSettings = {
    'pdSendPath': '/Applications/Pd-0.48-1.app/Contents/Resources/bin/pdsend'
}

SoundSets = {
    '../media/set1': {
        'mode': 'SINGLE_HIT'
    },
    '../media/loops1': {
        'mode': 'LOOP'
    }
    
}
SensorNames = {
    "68:C6:3A:C3:04:5E": "A 1", "A2": "A 2", "A3": "A 3", "A4": "A 4", "A5" : "A 5",
    "B1": "B 1", "B2": "B 2", "B3": "B 3", "B4": "B 4", "B5" : "B 5",
    "C1": "C 1", "C2": "C 2", "C3": "C 3", "C4": "C 4", "C5" : "C 5",
    "D1": "D 1", "D2": "D 2", "D3": "D 3", "D4": "D 4", "D5" : "D 5",
    "E1": "E 1", "E2": "E 2", "E3": "E 3", "E4": "E 4", "E5" : "E 5"
}
Controller = {
    "steps": [
        {
            'startTime': '21:18:15',
            'mqttCommand': '',
            'pdCommand': '',
            'set': '../media/set1'
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
            'set': '../media/set1'
        }
    ]
}
