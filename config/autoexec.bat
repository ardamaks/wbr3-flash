startDriver TuyaMCU
tuyaMcu_setBaudRate 9600
tuyaMcu_defWiFiState 4
// ch1 heating on/off (dp1)
linkTuyaMCUOutputToChannel 1 bool 1
setChannelType 1 Toggle
setChannelLabel 1 Heating
// ch2 mode (dp2)
linkTuyaMCUOutputToChannel 2 enum 2
setChannelType 2 ReadOnly
setChannelLabel 2 Mode
// ch3 target temp x10 (dp16)
linkTuyaMCUOutputToChannel 16 val 3
setChannelType 3 TextField
setChannelLabel 3 Target_x10
// ch4 room temp x10 (dp24), ch5 floor temp x10 (dp106)
linkTuyaMCUOutputToChannel 24 val 4
setChannelType 4 Temperature_div10
setChannelLabel 4 Room
linkTuyaMCUOutputToChannel 106 val 5
setChannelType 5 Temperature_div10
setChannelLabel 5 Floor
// ch6 heating active / relay (dp101)
linkTuyaMCUOutputToChannel 101 bool 6
setChannelType 6 ReadOnly
setChannelLabel 6 Heating_active
