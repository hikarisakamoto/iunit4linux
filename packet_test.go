package main

import "testing"

func TestDigits(t *testing.T) {
	got := digits(Reading{Temp: 44.3, Valid: true})
	want := [3]byte{4, 4, 3}
	if got != want {
		t.Errorf("got %v, want %v", got, want)
	}
}
