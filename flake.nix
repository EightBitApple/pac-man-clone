{
  description = ''
    Nix development shell for Pac Man Clone.

    Code for flake adapted from Vimjoyer's tutorial about flake-based devshells:
    https://github.com/vimjoyer/devshells-video

    The snippet to select Python packages was adapted from NixOS Wiki:
    https://wiki.nixos.org/wiki/Python
  '';

  inputs = {
    nixpkgs.url = "nixpkgs/nixos-24.05";
  };

  outputs =
    { nixpkgs, ... }@inputs:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
    in
    {
      devShells.x86_64-linux.default = pkgs.mkShell {
        packages = [
          (pkgs.python312.withPackages (
            python-pkgs: with python-pkgs; [
              # select Python packages here
              pygame
              pytmx
              cryptography
            ]
          ))
        ];

        shellHook = ''
          echo -e "\033[0;36mWelcome to the development shell.
          Run 'python main.py' to run the game!"
        '';
      };
    };
}
