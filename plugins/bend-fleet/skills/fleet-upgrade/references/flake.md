# The flake a fleet package carries

Three inputs, all following one nixpkgs and one bend. bolt is not an input:
ez's nix lib builds it from the lock's `[tools.bolt]`.

```nix
{
  description = "snap: program runner for Bend 2";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  inputs.bend = {
    url = "github:bendlang/bend";
    inputs.nixpkgs.follows = "nixpkgs";
  };
  inputs.ez = {
    url = "github:Emerging-Patterns/ez";
    inputs.nixpkgs.follows = "nixpkgs";
    inputs.bend.follows = "bend";
  };

  outputs = { self, nixpkgs, ... }@inputs:
    let
      system = "x86_64-linux";
      ez = inputs.ez.lib.${system};
      ezBin = inputs.ez.packages.${system}.default;
      bend = inputs.bend.packages.${system}.default;
      bolt = ez.toolPackage { name = "bolt"; src = self; inherit bend; wrapFlags = [ "--gpu" "off" ]; };
      bend-cc = ez.bend-cc;
      demo = ez.mkPackage { inherit bend; src = self; pname = "demo"; version = "1.0.0"; entry = "examples/demo/main.bend"; };
    in {
      packages.${system} = { inherit bend demo bend-cc; ez = ezBin; inherit bolt; default = demo; };
      apps.${system}.default = { type = "app"; program = "${demo}/bin/demo"; };
      checks.${system} = {
        inherit demo;
        proofs = ez.mkProofs { ez = ezBin; src = self; };
        lint = ez.mkLint { src = self; };          # bolt from ez.lock.toml [tools.bolt]
      };
      devShells.${system}.default = ez.mkShell {
        src = self;                                # adds every locked [tools.*]
        packages = [ bend bend-cc ezBin ];
      };
    };
}
```

and in `ez.toml`:

```toml
[tools.bolt]
git = "https://github.com/Emerging-Patterns/bolt"
tag = "v1.8.0"
root = "."
entry = "main.bend"
```

After `ez lock --upgrade --package bolt` and `nix flake lock`, `flake.lock`
holds exactly `bend`, `ez` and `nixpkgs`, with no `bolt` and no `ez_2`. If it
still has either, some input is missing its `follows`.

ez's lib (`nix/lib.nix`): `mkPackage`, `mkProofs { ez, src, name?, lock?,
bendLib? }`, `mkLint { src, bolt?, bend?, name?, lock?, bendLib? }`,
`toolPackage { name, src, bend?, lock?, wrapFlags?, … }`, `devPackages src`,
`mkShell { packages, extraHook?, src? }`, `mkFresh` (ez's own fresh-clone
check).
