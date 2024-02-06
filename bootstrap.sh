#!/bin/bash

cat <<EOF >start.sh
#!/bin/bash

SINGULARITY_PATH=/cvmfs/unpacked.cern.ch/registry.hub.docker.com/
SINGULARITY_IMAGE=fnallpc/fnallpc-docker:tensorflow-2.12.0-gpu-singularity

SINGULARITY_SHELL=\$(which bash) singularity exec -p -B \${PWD}:/srv --pwd /srv --nv \\
  \${SINGULARITY_PATH}/\${SINGULARITY_IMAGE} \\
  /bin/bash --rcfile /srv/.bashrc
EOF

cat <<EOF >.bashrc
install_env() {
  set -e
  echo "Installing shallow virtual environment in \$PWD/.env..."
  python -m venv --without-pip --system-site-packages .env
  unlink .env/lib64
  export TMPDIR=\$(mktemp -d -p .)
  .env/bin/python -m ipykernel install --user
  rm -rf \$TMPDIR && unset TMPDIR
  if [[ ! -d "./sipmpdf" ]]; then
    git clone https://github.com/UMDCMS/sipmpdf.git
  fi
  if [[ ! -d "./sipmanalyze" ]]; then
    git clone https://github.com/UMDCMS/sipmanalyze.git
  fi
  .env/bin/python -m pip install -q -e ./sipmpdf
  .env/bin/python -m pip install -q -e ./sipmanalyze
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
