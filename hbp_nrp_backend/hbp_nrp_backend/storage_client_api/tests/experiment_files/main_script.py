# Run a simulation until timeout

# log to file with file_logger
# change log level with file_logger.setLevel(level)
# e.g. file_logger.setLevel(logging.INFO)
# see https://docs.python.org/3/library/logging.html#logging-levels

try:
    while True:

        _ = nrp.run_loop()

except NRPSimulationTimeout:
    file_logger.debug("DEBUG NRPSimulationTimeout reached in script")
    file_logger.info("INFO NRPSimulationTimeout reached in script")
