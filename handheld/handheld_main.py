from handheld_db_module import sync_databases
from handheld_rfid_module import run_rfid_read

'''main() can be modified to suit processes done by select_action() function better. For now, this is just placeholder code'''
def main():
    action = 0

    try:
        if action == 1:
            run_rfid_read()
        
        elif action == 2:
            sync_databases()
    except:
        return None
        
'''select_action() is to be integrated with the UI to select which action to do -- Scan/Report Vehicle RFID or Sync Databases'''
#def select_action():

if __name__ == '__main__':
    main()