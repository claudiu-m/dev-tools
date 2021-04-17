#!/bin/bash
# Session Name
session="test"

gcc ./tgen_serv.c -lpthread -o tgen_serv

# Start New Session with our name
tmux new-session -d -s $session

# Name first Window and start test1
tmux rename-window -t 0 'test1'
tmux send-keys -t 'test1' './tgen_serv 32000 8' C-m
tmux split-window -v

# Create and setup pane for hugo server
#tmux new-window -t $session:1 -n 'test2'
tmux send-keys -t 'test1' 'python3 tgen_sink.py localhost 32000 8' C-m

#tmux split-window -v
#tmux send-keys -t 'test1' 'sudo tcpdump -i localhost' C-m

# Attach Session, on the Main window
tmux attach-session -t $session:0
