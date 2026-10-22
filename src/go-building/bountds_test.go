package main

import "testing"

func TestClampDisplay(t *testing.T) {
	got := clampDisplay(120)
	want := 99
	if got != want {
		t.Errorf("clampDisplay(120) = %d, want %d", got, want)
	}
}
