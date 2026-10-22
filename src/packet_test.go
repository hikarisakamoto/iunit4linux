package main

import "testing"

func TestBuildPacket(t *testing.T) {
	cases := []struct {
		name     string
		cpu, gpu Reading
		want     [12]byte
	}{
		{
			"vector",
			Reading{44.3, true},
			Reading{42.0, true},
			[12]byte{0x55, 0xAA, 0x01, 0x01, 0x06, 4, 4, 3, 4, 2, 0, 0x18},
		},
		{
			"blank",
			Reading{},
			Reading{},
			[12]byte{0x55, 0xAA, 0x01, 0x01, 0x06, 0xEE, 0xEE, 0xEE, 0xEE, 0xEE, 0xEE, 0x9B},
		},
		{
			"cpu only",
			Reading{44.3, true},
			Reading{},
			[12]byte{0x55, 0xAA, 0x01, 0x01, 0x06, 4, 4, 3, 0xEE, 0xEE, 0xEE, 0xDC},
		},
		{
			"gpu only",
			Reading{},
			Reading{42.0, true},
			[12]byte{0x55, 0xAA, 0x01, 0x01, 0x06, 0xEE, 0xEE, 0xEE, 4, 2, 0, 0xD7},
		},
	}
	for _, tc := range cases {
		got := buildPacket(tc.cpu, tc.gpu)
		if got != tc.want {
			t.Errorf("%s:\n got %X\nwant %X", tc.name, got, tc.want)
		}
		var sum uint32
		for _, b := range got[:11] {
			sum += uint32(b)
		}
		if byte(sum) != got[11] {
			t.Errorf("%s: checksum %02X does not match body", tc.name, got[11])
		}
	}
}

func TestDigits(t *testing.T) {
	cases := []struct {
		in   Reading
		want [3]byte
	}{
		{Reading{44.3, true}, [3]byte{4, 4, 3}},
		{Reading{7.0, true}, [3]byte{0, 7, 0}},
		{Reading{44.31, true}, [3]byte{4, 4, 3}},
		{Reading{44.36, true}, [3]byte{4, 4, 4}},
		{Reading{9.96, true}, [3]byte{1, 0, 0}},
		{Reading{0.0, true}, [3]byte{0, 0, 0}},
		{Reading{99.9, true}, [3]byte{9, 9, 9}},
		{Reading{150.0, true}, [3]byte{9, 9, 9}},
		{Reading{-5.0, true}, [3]byte{0, 0, 0}},
		{Reading{44.3, false}, [3]byte{0xEE, 0xEE, 0xEE}},
		{Reading{}, [3]byte{0xEE, 0xEE, 0xEE}},
	}
	for _, tc := range cases {
		if got := digits(tc.in); got != tc.want {
			t.Errorf("digits(%v) = %v, want %v", tc.in, got, tc.want)
		}
	}
}
