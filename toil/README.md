Toil
====

TODO: Maybe put `doc/toil.md` here.

Directory structure:

    toil/
      dummy.Dockerfile
      dev-minimal.Dockerfile

      # Shell functions to install dependencies
      # like ubuntu-deps, py2, etc.
      # Invoked by the Docker build.
      build-images.sh

      # stuff that happens outside the VM
      # Invocation of images; docker permissions hack
      vm-setup.sh

    services/
      # stuff that happens inside the VM
      toil-worker

