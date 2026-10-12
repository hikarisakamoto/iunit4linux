package main

import "math"

type Reading struct {
	Temp  float64
	Valid bool
}

func digits(r Reading) [3]byte {
	v := int(math.Ceil(r.Temp * 10))
	return [3]byte{byte(v / 100), byte(v / 10 % 10), byte(v % 10)}
}
