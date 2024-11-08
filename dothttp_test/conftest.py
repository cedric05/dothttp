def pytest_addoption(parser):
    parser.addoption(
        "--prefix", action="store", type=str, help="prefix for httpdef name", default="*"
    )
    parser.addoption(
        "--directory",
        action="store",
        nargs="+",
        help="list of directories to search for httpdef files",
        default=["."],
    )
    parser.addoption("--property-file", help="property file")
    parser.addoption(
        "--no-cookie",
        help="cookie storage is disabled",
        action="store_const",
        const=True,
    )
    parser.addoption(
        "--env",
        help="environment to select in property file. properties will be enabled on FIFO",
        nargs="+",
        default=["*"],
    )
    parser.addoption("--property", help="list of property's",
                     nargs="+", default=[])
