##################################################################################################
#                                            OVERVIEW                                            #
#                                                                                                #
# Tests the global logger configuration defined in utils.logs_config.                            #
# Ensures INFO-level messages are logged and logger has a valid name.                            #
##################################################################################################

##################################################################################################
#                                            IMPORTS                                             #
##################################################################################################

from utils.logs_config import logger

##################################################################################################
#                                             TESTS                                              #
##################################################################################################


def test_logger_basic_usage(caplog):
    """
    Ensure the global logger is correctly configured and logs at expected levels.
    """
    with caplog.at_level("INFO"):
        logger.info("test message")
    assert any("test message" in rec.message for rec in caplog.records)
    assert logger.name != ""
