package main

import "testing"

func TestDigits(t *testing.T) {
	got := digits(Reading{Temp: 44.3, Valid: true})
	want := [3]byte{4, 4, 3}
	if got != want {
		t.Errorf("got %v, want %v", got, want)
	}
}

func TestLessThenMinValue(t *testing.T) {
	got := digits(Reading{Temp: -1.1, Valid: true})
	want := [3]byte{0, 0, 0}

	if got != want {
		t.Errorf("got %v, want %v", got, want)
	}
}

func TestGreaterThenMaxValue(t *testing.T) {
	got := digits(Reading{Temp: 123.45, Valid: true})
	want := [3]byte{9, 9, 9}

	if got != want {
		t.Errorf("got %v, want %v", got, want)
	}
}

func TestInvalidReturnBlankValue(t *testing.T) {
	got := digits(Reading{Temp: 0.0, Valid: false})
	want := [3]byte{0xEE, 0xEE, 0xEE}

	if got != want {
		t.Errorf("got %v, want %v", got, want)
	}
}
