package isx1

import (
	"bytes"
	"encoding/hex"
	"encoding/json"
	"math/big"
	"os"
	"path/filepath"
	"runtime"
	"testing"
)

type vectorFile struct {
	Schema   string           `json:"schema"`
	Positive []positiveVector `json:"positive"`
	Invalid  []invalidVector  `json:"invalid"`
}

type positiveVector struct {
	Name             string   `json:"name"`
	FrameHex         string   `json:"frame_hex"`
	Resolution       string   `json:"resolution"`
	AddressSHA256    string   `json:"address_sha256"`
	RegistryRevision uint64   `json:"registry_revision"`
	RegistryHash     string   `json:"registry_hash"`
	SequenceHex      []string `json:"sequence_hex"`
}

type invalidVector struct {
	Name     string `json:"name"`
	FrameHex string `json:"frame_hex"`
	Reason   string `json:"reason"`
}

func loadVectors(t *testing.T) vectorFile {
	t.Helper()
	_, source, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("runtime.Caller failed")
	}
	path := filepath.Join(filepath.Dir(source), "..", "..", "..", "conformance", "isx1", "experimental_vectors_v0.1.json")
	raw, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	var vectors vectorFile
	if err := json.Unmarshal(raw, &vectors); err != nil {
		t.Fatal(err)
	}
	return vectors
}

func TestPositiveVectors(t *testing.T) {
	vectors := loadVectors(t)
	for _, vector := range vectors.Positive {
		t.Run(vector.Name, func(t *testing.T) {
			raw, err := hex.DecodeString(vector.FrameHex)
			if err != nil {
				t.Fatal(err)
			}
			frame, err := Decode(raw)
			if err != nil {
				t.Fatal(err)
			}
			name, err := ResolutionName(frame.Resolution)
			if err != nil {
				t.Fatal(err)
			}
			if name != vector.Resolution {
				t.Fatalf("resolution: got %s want %s", name, vector.Resolution)
			}
			if hex.EncodeToString(frame.AddressDigest[:]) != vector.AddressSHA256 {
				t.Fatal("address digest mismatch")
			}
			if frame.RegistryRevision != vector.RegistryRevision {
				t.Fatal("registry revision mismatch")
			}
			if hex.EncodeToString(frame.RegistryHash[:]) != vector.RegistryHash {
				t.Fatal("registry hash mismatch")
			}
			if len(frame.Sequence) != len(vector.SequenceHex) {
				t.Fatalf("sequence length: got %d want %d", len(frame.Sequence), len(vector.SequenceHex))
			}
			for i, wantHex := range vector.SequenceHex {
				want := new(big.Int)
				if _, ok := want.SetString(wantHex, 16); !ok {
					t.Fatalf("bad expected sequence hex %q", wantHex)
				}
				if frame.Sequence[i].Cmp(want) != 0 {
					t.Fatalf("sequence[%d] mismatch", i)
				}
			}
			encoded, err := Encode(frame)
			if err != nil {
				t.Fatal(err)
			}
			if !bytes.Equal(encoded, raw) {
				t.Fatal("canonical re-encode mismatch")
			}
		})
	}
}

func TestInvalidVectors(t *testing.T) {
	vectors := loadVectors(t)
	for _, vector := range vectors.Invalid {
		t.Run(vector.Name, func(t *testing.T) {
			raw, err := hex.DecodeString(vector.FrameHex)
			if err != nil {
				t.Fatal(err)
			}
			if _, err := Decode(raw); err == nil {
				t.Fatalf("expected rejection: %s", vector.Reason)
			}
		})
	}
}
