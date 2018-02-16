#CHIPSEC: Platform Security Assessment Framework
#Copyright (c) 2018, Eclypsium, Inc.
# 
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; Version 2.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#

"""
This module checks if the system has debug features turned on, 
specifiaclly the Direct Connect Interface (DCI).

This module checks the following bits:
1. HDCIEN bit in the DCI Control Register
2. Debug enable bit in the IA32_DEBUG_INTERFACE MSR
3. Debug lock bit in the IA32_DEBUG_INTERFACE MSR
4. Debug occured bit in the IA32_DEBUG_INTERFACE MSR

The module returns the following results:
FAILED : Any one of the debug features is enabled or unlocked.
PASSED : All debug feature are diabled and locked.

Hardware registers used:
IA32_DEBUG_INTERFACE[DEBUGENABLE]
IA32_DEBUG_INTERFACE[DEBUGELOCK]
IA32_DEBUG_INTERFACE[DEBUGEOCCURED]
P2SB_DCI.DCI_CONTROL_REG[HDCIEN]

"""

from chipsec.module_common import *
import chipsec.chipset
import chipsec.defines
_MODULE_NAME = 'debugenabled'


import chipsec.hal.uefi
import chipsec.hal.uefi_common

EDX_ENABLE_STATE = 0x00000000
IA32_DEBUG_INTERFACE_MSR = 0xC80
P2SB_DCI_PORT_ID = 0xB8
DCI_CONTROL_REG_OFFSET = 0x4

HDCIEN_MASK = 0b00000000000000000000000000010000
IA32_DEBUG_INTERFACE_DEBUGENABLE_MASK = 0b00000000000000000000000000000001
IA32_DEBUG_INTERFACE_DEBUGELOCK_MASK = 0b01000000000000000000000000000000
IA32_DEBUG_INTERFACE_DEBUGEOCCURED_MASK = 0b10000000000000000000000000000000 


########################################################################################################
#
# Main module functionality
#
########################################################################################################

class debugenabled(chipsec.module_common.BaseModule):



    def __init__(self):
        BaseModule.__init__(self)

    def is_supported(self):
        current_platform_id = self.cs.get_chipset_id()
        supported = (current_platform_id == chipsec.chipset.CHIPSET_ID_CFL) | (current_platform_id == chipsec.chipset.CHIPSET_ID_KBL) | (current_platform_id == chipsec.chipset.CHIPSET_ID_SKL)
        if not supported: self.logger.log_skipped_check( "DCI is not supported in this platform" )
        return supported


    def check_dci( self ):
        TestFail = False;
        self.logger.log( "[X] Checking DCI register status" )
        value = self.cs.msgbus.mm_msgbus_reg_read(P2SB_DCI_PORT_ID,DCI_CONTROL_REG_OFFSET)
        if self.logger.VERBOSE: self.logger.log( '[*] DCI Control Register = 0x%X' % value )
        HDCIEN = ((value & HDCIEN_MASK) == HDCIEN_MASK)
        if HDCIEN:
            TestFail = True;
        return TestFail

    def check_cpu_debug_enable( self ):
        self.logger.log( "[X] Checking IA32_DEBUG_INTERFACE msr status" )
        TestFail = False;
        for tid in range(self.cs.msr.get_cpu_thread_count()):
            (eax, edx) = self.cs.helper.read_msr( tid, IA32_DEBUG_INTERFACE_MSR )
            if self.logger.VERBOSE: self.logger.log('[cpu%d] RDMSR( 0x%x ): EAX = 0x%08X, EDX = 0x%08X' % (tid, IA32_DEBUG_INTERFACE_MSR, eax, edx) )
            IA32_DEBUG_INTERFACE_DEBUGENABLE = ((IA32_DEBUG_INTERFACE_DEBUGENABLE_MASK & eax) == IA32_DEBUG_INTERFACE_DEBUGENABLE_MASK)
            IA32_DEBUG_INTERFACE_DEBUGELOCK = ((IA32_DEBUG_INTERFACE_DEBUGELOCK_MASK & eax) == IA32_DEBUG_INTERFACE_DEBUGELOCK_MASK)
            IA32_DEBUG_INTERFACE_DEBUGEOCCURED = ((IA32_DEBUG_INTERFACE_DEBUGEOCCURED_MASK & eax) == IA32_DEBUG_INTERFACE_DEBUGEOCCURED_MASK)
            if edx == EDX_ENABLE_STATE: #Sanity check only EAX matters
                if (IA32_DEBUG_INTERFACE_DEBUGENABLE) or (IA32_DEBUG_INTERFACE_DEBUGELOCK) or (IA32_DEBUG_INTERFACE_DEBUGEOCCURED):
                    TestFail = True;
        return TestFail

    def run( self, module_argv ):
        if len(module_argv) > 2:
            self.logger.error( 'Not expecting any arguments' )
            return ModuleResult.ERROR
        returned_result = ModuleResult.PASSED;
        self.logger.start_test( "Debug features test" )
        script_pa = None
        dci_test_fail = self.check_dci();
        cpu_debug_test_fail = self.check_cpu_debug_enable();
            
        if dci_test_fail == True:
            self.logger.log_failed_check( 'DCI Debug is enabled' )
            returned_result = ModuleResult.FAILED
        if cpu_debug_test_fail == True:
            self.logger.log_failed_check( 'CPU IA32_DEBUG_INTERFACE is enabled' )
            returned_result = ModuleResult.FAILED
        
        return returned_result


        