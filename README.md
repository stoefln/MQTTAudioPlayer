# MQTT Audio Player
This source code is part of a bigger art project. The MQTT Audio Player receives command through MQTT and triggers sounds, depending on the current mode (which can change from time to time). The MQTT messages are sent by 25 sensors and trigger one of 25 sounds. 

## Pure Data Player
Samples are organised in rows (A-E) and columns (1-5) -> 25 slots for samples. 
The Pure data player takes care of polyphony and sample pannning (left-right, back-front)

Before sending commands via command line `pdsend`, pure data has to be started and the file puredata/pdAudioPlayer.pd has to be opened.

### Loading patches
Single audio file can be loaded with:
`echo "A 1 load ../media/A1.wav" | pdsend 3000 localhost udp`

Several audio files can be loaded with:
`echo "A 1 load ../media/A1.wav, A 2 load ../media/A2.wav, A 3 load ../media/A3.wav, A 4 load ../media/A4.wav, A 5 load ../media/A5.wav" | pdsend 3000 localhost udp`

### Controlling single samples
Samples can be played once via
`echo "A 1 play" | pdsend 3000 localhost udp`

Volume can be adjusted via
`echo "A 1 volume 0.5" | pdsend 3000 localhost udp`

Play can be stoped via
`echo "A 1 stop" | pdsend 3000 localhost udp`

### Controlling all samples at once
Samples can be played once via
`echo "all play" | pdsend 3000 localhost udp`

Volume can be adjusted via
`echo "all volume 0.5" | pdsend 3000 localhost udp`

Play can be stoped via
`echo "all stop" | pdsend 3000 localhost udp`

### Looping samples
Looping can be started by supplying the BPM to the loop start command
`echo "loop start 120" | pdsend 3000 localhost udp`

Looping can be stoped like this
`echo "loop stop" | pdsend 3000 localhost udp`