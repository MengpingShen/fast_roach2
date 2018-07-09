#!/bin/bash

session_name="mb"
mb_rows=7
mb_cols=3
mb_panes=19
mb_max_pane=$(($mb_panes - 1))

function pane-matrix() {
	rows=$1
	cols=$2
	for i in $(seq $rows -1 2); do
		tmux split-window -v -p $((100 - 100 / $i))
	done
	for i in $(seq $cols -1 2); do
		for r in $(seq 0 $(($rows - 1))); do
			w=$((100 - 100 / $i))
			tmux split-window -h -p $w -t $(($r + $rows*($cols-$i)))
		done
	done
}

function mb-start() {
	tmux new-session -s $session_name -n "Multibeam" -d
	pane-matrix $mb_rows $mb_cols
	tmux -2 attach-session -t mb
}

function mb-stop() {
	tmux kill-session -t $session_name
}

function mb-run() {
	for i in $(seq 0 $mb_max_pane); do
		tmux send-key -t $i "read line" Enter
	done
}

function mb-kill() {
	if [ "$1" == "-t" ]; then
		tmux send-key $1 $2 C-c
	else
		for i in $(seq 0 $mb_max_pane); do
			tmux send-key -t $i C-c
		done
	fi
}

function mb-runcmd() {
	if [ "$1" == "-t" ]; then
		tmux send-key "$*" Enter
	else
		for i in $(seq 0 $mb_max_pane); do
			tmux send-key -t $i "$*" Enter
		done
	fi
}

function mb() {
	cmd=$1
	shift
	case $cmd in
		"start")
			mb-start $*
			;;
		"stop")
			mb-stop $*
			;;
		"run")
			mb-run $*
			;;
		"kill")
			mb-kill $*
			;;
		"runcmd")
			mb-runcmd $*
			;;
		*)
			echo mb: Unknown command $cmd $*
			;;
	esac
}
