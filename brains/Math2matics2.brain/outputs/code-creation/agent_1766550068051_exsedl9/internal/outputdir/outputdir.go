package outputdir

import (
	"os"
	"path/filepath"
)

const (
	// EnvVarName is the environment variable that can override the default outputs directory.
	EnvVarName = "OUTPUT_DIR"

	// DefaultOutputsDir is used when OUTPUT_DIR is unset or empty.
	DefaultOutputsDir = "./outputs"
)

// GetOutputsDir returns the outputs directory path used by the pipeline.
// It defaults to ./outputs, respects OUTPUT_DIR when set, cleans the path,
// and ensures the directory exists (creating it if necessary).
func GetOutputsDir() (string, error) {
	dir := os.Getenv(EnvVarName)
	if dir == "" {
		dir = DefaultOutputsDir
	}
	dir = filepath.Clean(dir)

	if err := os.MkdirAll(dir, 0o755); err != nil {
		return "", err
	}
	return dir, nil
}
