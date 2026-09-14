package isx1

import (
	"bytes"
	"encoding/binary"
	"errors"
	"fmt"
	"hash/crc32"
	"math/big"
)

var Magic = []byte("ISX1")

const (
	Version          = byte(1)
	KindSpectral     = byte(1)
	BlockSize        = 16
	MaxBitWidth      = 4096
	MaxSequenceItems = 1_000_000
	MaxVarintBytes   = 10
	WidthMarker      = byte(0xFF)
)

type Frame struct {
	Resolution       byte
	AddressDigest    [32]byte
	RegistryRevision uint64
	RegistryHash     [32]byte
	Sequence         []*big.Int
}

func resolutionName(id byte) (string, error) {
	switch id {
	case 1:
		return "R1", nil
	case 2:
		return "R2", nil
	default:
		return "", fmt.Errorf("unsupported resolution: %d", id)
	}
}

func encodeUVarint(v uint64) []byte {
	out := make([]byte, 0, 10)
	for {
		b := byte(v & 0x7f)
		v >>= 7
		if v != 0 {
			out = append(out, b|0x80)
		} else {
			return append(out, b)
		}
	}
}

func decodeUVarint(data []byte, pos int) (uint64, int, error) {
	start := pos
	var v uint64
	var shift uint
	for {
		if pos >= len(data) {
			return 0, pos, errors.New("truncated varint")
		}
		if pos-start >= MaxVarintBytes {
			return 0, pos, errors.New("varint too large")
		}
		b := data[pos]
		pos++
		part := uint64(b & 0x7f)
		if shift >= 64 && part != 0 {
			return 0, pos, errors.New("varint overflow")
		}
		if shift < 64 {
			if part > (^uint64(0) >> shift) {
				return 0, pos, errors.New("varint overflow")
			}
			v |= part << shift
		}
		if b&0x80 == 0 {
			if !bytes.Equal(data[start:pos], encodeUVarint(v)) {
				return 0, pos, errors.New("noncanonical varint")
			}
			return v, pos, nil
		}
		shift += 7
	}
}

func encodeWidth(width int) ([]byte, error) {
	if width < 0 || width > MaxBitWidth {
		return nil, errors.New("invalid block width")
	}
	if width < int(WidthMarker) {
		return []byte{byte(width)}, nil
	}
	return append([]byte{WidthMarker}, encodeUVarint(uint64(width))...), nil
}

func decodeWidth(data []byte, pos int) (int, int, error) {
	if pos >= len(data) {
		return 0, pos, errors.New("truncated block width")
	}
	first := data[pos]
	pos++
	if first != WidthMarker {
		return int(first), pos, nil
	}
	width, next, err := decodeUVarint(data, pos)
	if err != nil {
		return 0, next, err
	}
	if width < uint64(WidthMarker) {
		return 0, next, errors.New("noncanonical extended width")
	}
	if width > MaxBitWidth {
		return 0, next, errors.New("block width exceeds cap")
	}
	return int(width), next, nil
}

func encodeBlock(values []*big.Int) ([]byte, error) {
	if len(values) == 0 || len(values) > BlockSize {
		return nil, errors.New("invalid block length")
	}
	width := 0
	for _, v := range values {
		if v == nil || v.Sign() < 0 {
			return nil, errors.New("nonnegative integer required")
		}
		if v.BitLen() > width {
			width = v.BitLen()
		}
	}
	if width > MaxBitWidth {
		return nil, errors.New("value too wide")
	}
	header, err := encodeWidth(width)
	if err != nil {
		return nil, err
	}
	if width == 0 {
		return header, nil
	}

	totalBits := width * len(values)
	padding := (8 - totalBits%8) % 8
	acc := new(big.Int)
	for _, v := range values {
		acc.Lsh(acc, uint(width))
		acc.Or(acc, v)
	}
	acc.Lsh(acc, uint(padding))
	byteCount := (totalBits + 7) / 8
	payload := acc.Bytes()
	if len(payload) < byteCount {
		padded := make([]byte, byteCount)
		copy(padded[byteCount-len(payload):], payload)
		payload = padded
	}
	out := append([]byte{}, header...)
	out = append(out, payload...)
	return out, nil
}

func decodeBlock(data []byte, pos, count int) ([]*big.Int, int, error) {
	if count <= 0 || count > BlockSize {
		return nil, pos, errors.New("invalid block length")
	}
	start := pos
	width, next, err := decodeWidth(data, pos)
	if err != nil {
		return nil, next, err
	}
	pos = next
	if width == 0 {
		out := make([]*big.Int, count)
		for i := range out {
			out[i] = new(big.Int)
		}
		return out, pos, nil
	}

	totalBits := width * count
	byteCount := (totalBits + 7) / 8
	if pos+byteCount > len(data) {
		return nil, pos, errors.New("truncated block")
	}
	raw := data[pos : pos+byteCount]
	pos += byteCount
	acc := new(big.Int).SetBytes(raw)
	padding := (8 - totalBits%8) % 8
	if padding != 0 {
		mask := new(big.Int).Sub(new(big.Int).Lsh(big.NewInt(1), uint(padding)), big.NewInt(1))
		if new(big.Int).And(new(big.Int).Set(acc), mask).Sign() != 0 {
			return nil, pos, errors.New("nonzero padding bits")
		}
		acc.Rsh(acc, uint(padding))
	}

	valueMask := new(big.Int).Sub(new(big.Int).Lsh(big.NewInt(1), uint(width)), big.NewInt(1))
	out := make([]*big.Int, 0, count)
	maxWidth := 0
	for i := 0; i < count; i++ {
		shift := uint(width * (count - 1 - i))
		v := new(big.Int).Rsh(new(big.Int).Set(acc), shift)
		v.And(v, valueMask)
		if v.BitLen() > maxWidth {
			maxWidth = v.BitLen()
		}
		out = append(out, v)
	}
	if maxWidth != width {
		return nil, pos, errors.New("nonminimal block width")
	}
	reencoded, err := encodeBlock(out)
	if err != nil {
		return nil, pos, err
	}
	if !bytes.Equal(reencoded, data[start:pos]) {
		return nil, pos, errors.New("noncanonical block")
	}
	return out, pos, nil
}

func Decode(data []byte) (*Frame, error) {
	if len(data) < 79 {
		return nil, errors.New("truncated frame")
	}
	body := data[:len(data)-4]
	gotCRC := binary.BigEndian.Uint32(data[len(data)-4:])
	if crc32.ChecksumIEEE(body) != gotCRC {
		return nil, errors.New("checksum mismatch")
	}
	if len(body) < 8 || !bytes.Equal(body[:4], Magic) {
		return nil, errors.New("invalid magic")
	}
	pos := 4
	if body[pos] != Version {
		return nil, errors.New("unsupported version")
	}
	pos++
	if body[pos] != KindSpectral {
		return nil, errors.New("unsupported kind")
	}
	pos++
	resolution := body[pos]
	if _, err := resolutionName(resolution); err != nil {
		return nil, err
	}
	pos++
	if body[pos] != 0 {
		return nil, errors.New("unsupported flags")
	}
	pos++

	var addr [32]byte
	if pos+32 > len(body) {
		return nil, errors.New("truncated address")
	}
	copy(addr[:], body[pos:pos+32])
	pos += 32

	revision, next, err := decodeUVarint(body, pos)
	if err != nil {
		return nil, err
	}
	pos = next

	var registryHash [32]byte
	if pos+32 > len(body) {
		return nil, errors.New("truncated registry hash")
	}
	copy(registryHash[:], body[pos:pos+32])
	pos += 32

	itemCount64, next, err := decodeUVarint(body, pos)
	if err != nil {
		return nil, err
	}
	pos = next
	if itemCount64 == 0 || itemCount64 > MaxSequenceItems {
		return nil, errors.New("invalid sequence length")
	}
	itemCount := int(itemCount64)

	sequence := make([]*big.Int, 0, itemCount)
	remaining := itemCount
	for remaining > 0 {
		count := BlockSize
		if remaining < count {
			count = remaining
		}
		block, next, err := decodeBlock(body, pos, count)
		if err != nil {
			return nil, err
		}
		pos = next
		sequence = append(sequence, block...)
		remaining -= count
	}
	if pos != len(body) {
		return nil, errors.New("trailing bytes")
	}

	result := &Frame{
		Resolution:       resolution,
		AddressDigest:    addr,
		RegistryRevision: revision,
		RegistryHash:     registryHash,
		Sequence:         sequence,
	}
	reencoded, err := Encode(result)
	if err != nil {
		return nil, err
	}
	if !bytes.Equal(reencoded, data) {
		return nil, errors.New("noncanonical frame")
	}
	return result, nil
}

func Encode(frame *Frame) ([]byte, error) {
	if frame == nil {
		return nil, errors.New("frame required")
	}
	if _, err := resolutionName(frame.Resolution); err != nil {
		return nil, err
	}
	if len(frame.Sequence) == 0 || len(frame.Sequence) > MaxSequenceItems {
		return nil, errors.New("invalid sequence length")
	}
	body := append([]byte{}, Magic...)
	body = append(body, Version, KindSpectral, frame.Resolution, 0)
	body = append(body, frame.AddressDigest[:]...)
	body = append(body, encodeUVarint(frame.RegistryRevision)...)
	body = append(body, frame.RegistryHash[:]...)
	body = append(body, encodeUVarint(uint64(len(frame.Sequence)))...)
	for i := 0; i < len(frame.Sequence); i += BlockSize {
		end := i + BlockSize
		if end > len(frame.Sequence) {
			end = len(frame.Sequence)
		}
		block, err := encodeBlock(frame.Sequence[i:end])
		if err != nil {
			return nil, err
		}
		body = append(body, block...)
	}
	out := append([]byte{}, body...)
	var checksum [4]byte
	binary.BigEndian.PutUint32(checksum[:], crc32.ChecksumIEEE(body))
	out = append(out, checksum[:]...)
	return out, nil
}

func ResolutionName(id byte) (string, error) {
	return resolutionName(id)
}
