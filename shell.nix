{ pkgs ? import <nixpkgs> {} }:
let
  # Haskell toolchain + LSP for working across AbsBox and ../Hastructure.
  # HLS must match the engine's GHC (ghc912 = 9.12.3); pkgs.haskell-language-server
  # targets the nixpkgs default GHC (9.10.x) and won't load the Hastructure project.
  hls = pkgs.haskell.packages.ghc912.haskell-language-server;
in
pkgs.mkShell {
  buildInputs = [
    pkgs.rustc
    pkgs.cargo
    pkgs.ninja 
    pkgs.python313
    pkgs.python313Packages.meson-python
    pkgs.python313Packages.pillow 
    pkgs.python313Packages.rpds-py 
    pkgs.python313Packages.cython
    pkgs.zeromq
    pkgs.gcc
    pkgs.uv
    pkgs.pkg-config
    pkgs.glibcLocales
    pkgs.graphviz
    pkgs.just
    # Haskell engine (../Hastructure) + language server
    pkgs.haskell.compiler.ghc912
    pkgs.cabal-install
    hls
    pkgs.zlib
  ];
  LANG = "en_US.UTF-8";
  LC_ALL = "en_US.UTF-8";
  LD_LIBRARY_PATH = "${pkgs.gcc.cc.lib}/lib:${pkgs.zeromq}/lib";

  shellHook = "
    source .venv/bin/activate
  ";
}
