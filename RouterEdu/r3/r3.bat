@ECHO OFF
dynamips-w2000.exe -P 7200 -p 1:PA-FE-TX -s 0:0:udp:10004:127.0.0.1:10003 -s 1:0:udp:10005:127.0.0.1:10006 --idle-pc=0x6095ca40 c7200-jk9o3s-mz.124-7.bin
