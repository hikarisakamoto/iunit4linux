package main

func clampDisplay(n int) int {
	if n < 0 {
		return 0
	}
	if n > 99 {
		return 99
	}
	return n
}
