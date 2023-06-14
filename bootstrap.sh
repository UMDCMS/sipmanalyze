#!/bin/bash

cat <<EOF >start.sh
#!/bin/bash

COFFEA_IMAGE=coffeateam/coffea-dask:0.7.21-fastjet-3.4.0.1-gc3d707c

SINGULARITY_SHELL=\$(which bash) singularity exec -p -B \${PWD}:/srv --pwd /srv \\
  /cvmfs/unpacked.cern.ch/registry.hub.docker.com/\${COFFEA_IMAGE} \\
  /bin/bash --rcfile /srv/.bashrc
EOF

cat <<EOF >.bashrc
install_env() {
  set -e
  echo "Installing shallow virtual environment in \$PWD/.env..."
  python -m venv --without-pip --system-site-packages .env
  unlink .env/lib64  # HTCondor can't transfer symlink to directory and it appears optional
  # work around issues copying CVMFS xattr when copying to tmpdir
  export TMPDIR=\$(mktemp -d -p .)
  .env/bin/python -m ipykernel install --user
  rm -rf \$TMPDIR && unset TMPDIR
  git clone https://github.com/UMDCMS/sipmpdf.git
  git clone https://github.com/UMDCMS/sipmanalyze.git
  .env/bin/python -m pip install -q ./sipmpdf
  .env/bin/python -m pip install -q ./sipmanalyze
  echo "done."
}

export JUPYTER_PATH=/srv/.jupyter
export JUPYTER_RUNTIME_DIR=/srv/.local/share/jupyter/runtime
export JUPYTER_DATA_DIR=/srv/.local/share/jupyter
export IPYTHONDIR=/srv/.ipython
unset GREP_OPTIONS

[[ -d .env ]] || install_env
source .env/bin/activate
EOF

chmod u+x start.sh
echo "Wrote start.sh and custom .bashrc to current directory. In the future ./start.sh to start the singularity shell!"