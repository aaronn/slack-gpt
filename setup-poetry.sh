# Sets up using `poetry` on Render
# `source`d in all Render scripts

set -euxo pipefail

# Use pipx to install Poetry to avoid Render's outdated Poetry install

poetry() {
    # Uses `pipx run` instead of `pipx install` to avoid ~/.local/bin
    # - Increases stability as less directories are involved that could be affected
    #   by Render's environment
    # - Avoids having to add `~/.local/bin` to PATH which could have side effects if
    #   Render has/adds binaries to ~/.local/bin
    # - Ensures we're always using our own Poetry install
    # Assumes Render allows writing to `~/.local/pipx/`
    pipx run poetry "$@"
}

install-poetry() {
    pip install -U pip
    # Assumes `pip install` location is in PATH
    pip install -U pipx
    # Install and smoke test Poetry
    # This keeps `poetry`'s perforamnce consistent and forces the slow initial run
    # to be during setup
    poetry --version
}
install-poetry
