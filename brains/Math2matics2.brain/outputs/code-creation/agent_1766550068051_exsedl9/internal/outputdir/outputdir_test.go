package outputdir

import (
	"os"
	"path/filepath"
	"testing"
)

func mustChdir(t *testing.T, dir string) func() {
	t.Helper()
	wd, err := os.Getwd()
	if err != nil {
		t.Fatalf("Getwd: %v", err)
	}
	if err := os.Chdir(dir); err != nil {
		t.Fatalf("Chdir(%q): %v", dir, err)
	}
	return func() {
		_ = os.Chdir(wd)
	}
}

func assertIsDir(t *testing.T, path string) {
	t.Helper()
	fi, err := os.Stat(path)
	if err != nil {
		t.Fatalf("expected dir %q to exist: %v", path, err)
	}
	if !fi.IsDir() {
		t.Fatalf("expected %q to be a directory", path)
	}
}
func TestGetOutputsDir_DefaultOutputs_CreatesDir(t *testing.T) {
	temp := t.TempDir()
	restore := mustChdir(t, temp)
	defer restore()

	t.Setenv("OUTPUT_DIR", "")

	got, err := GetOutputsDir()
	if err != nil {
		t.Fatalf("GetOutputsDir() error: %v", err)
	}

	want := filepath.Clean("./outputs")
	if got != want {
		t.Fatalf("GetOutputsDir()=%q, want %q", got, want)
	}

	assertIsDir(t, filepath.Join(temp, got))
}
func TestGetOutputsDir_EnvOverride_PathIsCleaned_CreatesDir(t *testing.T) {
	temp := t.TempDir()
	restore := mustChdir(t, temp)
	defer restore()

	t.Setenv("OUTPUT_DIR", filepath.Join("custom", "..", "out"))

	got, err := GetOutputsDir()
	if err != nil {
		t.Fatalf("GetOutputsDir() error: %v", err)
	}

	want := filepath.Clean(filepath.Join("custom", "..", "out"))
	if got != want {
		t.Fatalf("GetOutputsDir()=%q, want %q", got, want)
	}

	assertIsDir(t, filepath.Join(temp, got))
}
func TestGetOutputsDir_EnvOverride_AbsolutePath_CreatesDir(t *testing.T) {
	temp := t.TempDir()
	restore := mustChdir(t, temp)
	defer restore()

	abs := filepath.Join(temp, "abs-outputs")
	t.Setenv("OUTPUT_DIR", filepath.Join(abs, ".", "nested", ".."))

	got, err := GetOutputsDir()
	if err != nil {
		t.Fatalf("GetOutputsDir() error: %v", err)
	}

	want := filepath.Clean(filepath.Join(abs, ".", "nested", ".."))
	if got != want {
		t.Fatalf("GetOutputsDir()=%q, want %q", got, want)
	}

	assertIsDir(t, got)
}
