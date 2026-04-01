; ============================================================
; UEM Agent - NSIS Installer Script
; Requires: NSIS 3.x, NSExec plugin, AccessControl plugin
; Build:  makensis uem_agent.nsi
; ============================================================

Unicode True

!define PRODUCT_NAME      "UEM Agent"
!define PRODUCT_VERSION   "1.0.0"
!define PRODUCT_PUBLISHER "UEM Platform"
!define PRODUCT_URL       "https://your-uem-server"
!define SERVICE_NAME      "UEMAgentService"
!define SERVICE_DISPLAY   "UEM Agent Service"
!define INSTALL_DIR       "$PROGRAMFILES64\UEMAgent"
!define DATA_DIR          "$COMMONAPPDATA\UEMAgent"
!define UNINSTALL_KEY     "Software\Microsoft\Windows\CurrentVersion\Uninstall\UEMAgent"

;------------------------------------------------------------
; Modern UI
;------------------------------------------------------------
!include "MUI2.nsh"
!include "nsDialogs.nsh"
!include "LogicLib.nsh"
!include "x64.nsh"

Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "UEMAgentSetup-${PRODUCT_VERSION}.exe"
InstallDir "${INSTALL_DIR}"
RequestExecutionLevel admin
ShowInstDetails show
ShowUnInstDetails show

;------------------------------------------------------------
; MUI Pages
;------------------------------------------------------------
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\..\LICENSE"
Page custom ServerConfigPage ServerConfigPageLeave
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

;------------------------------------------------------------
; Custom page variables
;------------------------------------------------------------
Var ServerURL
Var EnrollToken
Var hServerURLInput
Var hTokenInput
Var Dialog

;------------------------------------------------------------
; Custom page: Server configuration
;------------------------------------------------------------
Function ServerConfigPage
    nsDialogs::Create 1018
    Pop $Dialog
    ${If} $Dialog == error
        Abort
    ${EndIf}

    ${NSD_CreateLabel} 0 0 100% 12u "UEM Server URL (e.g. https://192.168.1.100):"
    Pop $0
    ${NSD_CreateText} 0 14u 100% 14u "$ServerURL"
    Pop $hServerURLInput

    ${NSD_CreateLabel} 0 35u 100% 12u "Enrollment Token:"
    Pop $0
    ${NSD_CreateText} 0 49u 100% 14u "$EnrollToken"
    Pop $hTokenInput

    ${NSD_CreateLabel} 0 70u 100% 30u \
        "Enter the enrollment token generated from the UEM console.$\nLeave blank to enroll manually after installation."
    Pop $0

    nsDialogs::Show
FunctionEnd

Function ServerConfigPageLeave
    ${NSD_GetText} $hServerURLInput $ServerURL
    ${NSD_GetText} $hTokenInput $EnrollToken
FunctionEnd

;------------------------------------------------------------
; Installer sections
;------------------------------------------------------------
Section "UEM Agent" SecMain
    SectionIn RO  ; Required section

    SetOutPath "${INSTALL_DIR}"

    ; Stop existing service if running
    ExecWait 'sc stop "${SERVICE_NAME}"' $0
    Sleep 2000
    ExecWait 'sc delete "${SERVICE_NAME}"' $0
    Sleep 1000

    ; Copy main executable
    File "..\dist\UEMAgent.exe"

    ; Copy CA certificate if bundled with installer
    ${If} ${FileExists} "ca.crt"
        CreateDirectory "${DATA_DIR}\certs"
        File /oname=${DATA_DIR}\certs\ca.crt "ca.crt"
    ${EndIf}

    ; Create data directory
    CreateDirectory "${DATA_DIR}"
    CreateDirectory "${DATA_DIR}\certs"
    CreateDirectory "${DATA_DIR}\packages"
    CreateDirectory "${DATA_DIR}\logs"

    ; Install Windows service
    ExecWait '"${INSTALL_DIR}\UEMAgent.exe" install' $0
    DetailPrint "Service install exit code: $0"

    ; Run enrollment if server URL provided
    ${If} $ServerURL != ""
        DetailPrint "Enrolling with server: $ServerURL"
        ${If} $EnrollToken != ""
            ExecWait '"${INSTALL_DIR}\UEMAgent.exe" enroll --server "$ServerURL" --token "$EnrollToken"' $0
        ${Else}
            ExecWait '"${INSTALL_DIR}\UEMAgent.exe" enroll --server "$ServerURL"' $0
        ${EndIf}
        DetailPrint "Enrollment exit code: $0"
    ${EndIf}

    ; Start the service
    ExecWait 'sc start "${SERVICE_NAME}"' $0
    DetailPrint "Service start exit code: $0"

    ; Write uninstall registry keys
    WriteRegStr HKLM "${UNINSTALL_KEY}" "DisplayName"     "${PRODUCT_NAME}"
    WriteRegStr HKLM "${UNINSTALL_KEY}" "DisplayVersion"  "${PRODUCT_VERSION}"
    WriteRegStr HKLM "${UNINSTALL_KEY}" "Publisher"       "${PRODUCT_PUBLISHER}"
    WriteRegStr HKLM "${UNINSTALL_KEY}" "UninstallString" \
        '"${INSTALL_DIR}\Uninstall.exe"'
    WriteRegStr HKLM "${UNINSTALL_KEY}" "QuietUninstallString" \
        '"${INSTALL_DIR}\Uninstall.exe" /S'
    WriteRegStr HKLM "${UNINSTALL_KEY}" "InstallLocation" "${INSTALL_DIR}"
    WriteRegDWORD HKLM "${UNINSTALL_KEY}" "NoModify"      1
    WriteRegDWORD HKLM "${UNINSTALL_KEY}" "NoRepair"      1

    WriteUninstaller "${INSTALL_DIR}\Uninstall.exe"

    ; Add to PATH (optional — for CLI use)
    EnVar::SetHKLM
    EnVar::AddValue "PATH" "${INSTALL_DIR}"

SectionEnd

;------------------------------------------------------------
; Uninstaller
;------------------------------------------------------------
Section "Uninstall"
    ; Stop and delete service
    ExecWait 'sc stop "${SERVICE_NAME}"'
    Sleep 2000
    ExecWait '"${INSTALL_DIR}\UEMAgent.exe" remove'
    Sleep 1000
    ExecWait 'sc delete "${SERVICE_NAME}"'

    ; Remove files
    Delete "${INSTALL_DIR}\UEMAgent.exe"
    Delete "${INSTALL_DIR}\Uninstall.exe"
    RMDir "${INSTALL_DIR}"

    ; Remove data directory (preserve certs/config for re-enrollment)
    ; Uncomment below to also remove data:
    ; RMDir /r "${DATA_DIR}"

    ; Remove registry entries
    DeleteRegKey HKLM "${UNINSTALL_KEY}"

    ; Remove from PATH
    EnVar::SetHKLM
    EnVar::DeleteValue "PATH" "${INSTALL_DIR}"

SectionEnd

;------------------------------------------------------------
; Silent install support
; Usage: UEMAgentSetup.exe /S /SERVER=https://host /TOKEN=abc123
;------------------------------------------------------------
Function .onInit
    ${GetParameters} $R0

    ClearErrors
    ${GetOptions} $R0 "/SERVER=" $ServerURL
    ${If} ${Errors}
        StrCpy $ServerURL ""
    ${EndIf}

    ClearErrors
    ${GetOptions} $R0 "/TOKEN=" $EnrollToken
    ${If} ${Errors}
        StrCpy $EnrollToken ""
    ${EndIf}

    ; Skip config page in silent mode
    IfSilent 0 +2
        Abort

FunctionEnd

!include "FileFunc.nsh"
!insertmacro GetParameters
!insertmacro GetOptions
