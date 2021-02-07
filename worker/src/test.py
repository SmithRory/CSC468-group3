# This file is only for testing and can be deleted without any harm
# It's current purpose is for testing commands.

from cmd_handler import CMDHandler
from database.accounts import get_users

handler = CMDHandler()

handler.handle_command('ADD', ['user1', 50.00])
get_users()

handler.handle_command('ADD', ['user1', 20.00])
get_users()

handler.handle_command('BUY', ['user1', 'ABC', 30.00])
get_users()

handler.handle_command('COMMIT_BUY', ['user1'])
get_users()

handler.handle_command('BUY', ['user1', 'ABC', 20.00])

handler.handle_command('COMMIT_BUY', ['user1'])
get_users()

handler.handle_command('SELL', ['user1', 'ABC', 15.00])
get_users()

handler.handle_command('COMMIT_SELL', ['user1'])
get_users()

handler.handle_command('SELL', ['user1', 'ABC', 100.00])
get_users()

handler.handle_command('COMMIT_SELL', ['user1'])
get_users()