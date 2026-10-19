package main

import "math"

type Reading struct {
	Temp  float64
	Valid bool
}

var (
	blank   = [3]byte{0xEE, 0xEE, 0xEE}
	minTemp = 0.0
	maxTemp = 99.9
)

func digits(r Reading) [3]byte {
	if !r.Valid {
		return blank
	}

	t := r.Temp

	if t < minTemp {
		t = minTemp
	}

	if t > maxTemp {
		t = maxTemp
	}

	v := int(math.Round(t * 10))
	return [3]byte{byte(v / 100), byte(v / 10 % 10), byte(v % 10)}
}

func buildPacket(cpu, gpu Reading) [12]byte {
	var p [12]byte
	p[0], p[1] = 0x55, 0xAA
	p[2], p[3], p[4] = 0x01, 0x01, 0x06

	c, g := digits(cpu), digits(gpu)
	copy(p[5:8], c[:])
	copy(p[8:11], g[:])

	var sum uint32
	for _, b := range p[:11] {
		sum += uint32(b)
	}

	p[11] = byte(sum)
	return p
}
