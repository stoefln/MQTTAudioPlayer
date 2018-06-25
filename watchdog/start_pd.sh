#!/bin/bash
sudo puredata /home/pi/MAW_ArbeitIstUnsichtbar/03_LightRoom_Loop.pd &

sleep 10

while true
	do
	sudo touch /mnt/ramfolder/heartbeat_ref.txt
	sleep 6
	if [ "/mnt/ramfolder/heartbeat_ref.txt" -nt "/mnt/ramfolder/heartbeat_new.txt" ]; then
		echo "pd stopped"
		sudo shutdown -r now 
	else
		echo "all fine"
	fi
done
