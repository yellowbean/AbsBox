{ pkgs ? import <nixpkgs> {} }:
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
    pkgs.pkg-config
    pkgs.glibcLocales
  ];
  LANG = "en_US.UTF-8";
  LC_ALL = "en_US.UTF-8";
  LD_LIBRARY_PATH = "${pkgs.gcc.cc.lib}/lib:${pkgs.zeromq}/lib";

  shellHook = "
    source bin/activate
  ";
}
