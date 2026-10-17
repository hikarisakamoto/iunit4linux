package main

import "math"

type Reading struct {
	Temp  float64
	Valid bool
}

var (
	blank = [3]byte{0xEE, 0xEE, 0xEE}
	min   = 0.0
	max   = 99.9
)

func digits(r Reading) [3]byte {
	if !r.Valid {
		return blank
	}

	t := r.Temp

	if t < min {
		t = min
	}

	if t > max {
		t = max
	}

	v := int(math.Ceil(t))
	return [3]byte{byte(v / 100), byte(v / 10 % 10), byte(v % 10)}
}
