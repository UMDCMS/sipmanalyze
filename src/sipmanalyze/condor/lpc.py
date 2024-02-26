import os
import socket
import sys

import distributed
import lpcjobqueue


def make_lpc_cluster_client(jobs, transfer_input_files=None, **kwargs):
    """
    Setting up default requirements better taylored to what is typical for sipm
    analysis related items.
    """
    kwargs.setdefault("cores", 1)
    kwargs.setdefault("memory", "2GB")
    kwargs.setdefault("disk", "2GB")
    kwargs.setdefault("log_directory", None)
    kwargs.setdefault("job_extra_directives", {})
    kwargs.setdefault("shipenv", True)
    kwargs.setdefault("death_timeout", 240)
    kwargs.setdefault(
        "scheduler_options",  # Auto fixing the port number
        dict(dashboard_address=f":{__get_port():d}"),
    )
    kwargs["job_extra_directives"].update(  # Geting proxy file
        set_default_proxy(kwargs["job_extra_directives"])
    )

    # Setting up the additional files to be transfered
    if transfer_input_files is None:
        transfer_input_files = []
    base_path = os.abspath(os.path.dirname(sys.executable) + "../../")
    transfer_input_files.append(os.path.join(base_path, "sipmpdf/"))
    transfer_input_files.append(os.path.join(base_path, "sipmanalyze/"))

    # Creating the LPC cluster client pair
    cluster = lpcjobqueue.LPCCondorCluster(
        transfer_input_files=transfer_input_files, **kwargs
    )
    client = distributed.Client(cluster)
    print(
        "Scheduler is hosted at localhost:{:d}".format(
            cluster.scheduler_info["services"]["dashboard"]
        )
    )


    # Scale up the cluster to the desired number of workers
    cluster.scale(jobs)
    return cluster, client


def set_default_proxy(job_extra_directives):
    """
    Getting the default proxy files
    """
    proxyfile = ""
    if "x509userproxy" not in job_extra_directives:
        proxyfile = "{0}/x509up_u{1}".format(os.environ["HOME"], os.getuid())
        print("Using default proxy file:", proxyfile)
    else:
        proxyfile = job_extra_directives["x509userproxy"]

    # Checking if file is a valid file
    if not os.path.isfile(proxyfile):
        raise FileNotFoundError(
            f"""
            The proxy file {proxyfile} doesn't exist! Create the default proxy
            using the following command:
            > voms-proxy-init --voms cms --valid 192:00 --out ${{HOME}}/x509up_u${{UID}}
            """
        )

    return {"x509userproxy": proxyfile}


def __get_port() -> int:
    def _port_in_use(port: int) -> bool:
        """
        Checking if a port is currently in use. Solution from stack overflow:
        https://stackoverflow.com/questions/2470971/fast-way-to-test-if-a-port-is-in-use-using-python
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("localhost", port)) == 0

    for port in range(8787, 8787 + 100):
        if not _port_in_use(port):
            return port

    raise RunTimeError("No available port found!")
