#include <windows.h>
#include <stdio.h>

int main() {
    STARTUPINFO si;
    PROCESS_INFORMATION pi;
    BOOL success;
    
    // Initialize the STARTUPINFO structure
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    ZeroMemory(&pi, sizeof(pi));
    
    // Command to execute with arguments
    // Note: We use double quotes around the Python command since the inner command uses single quotes
    char command[] = "python.exe -c \"print('hi from python 3'); import sys; sys.exit(42)\"";
    
    // Create the process
    success = CreateProcess(
        NULL,           // No module name (use command line)
        command,        // Command line with arguments
        NULL,           // Process handle not inheritable
        NULL,           // Thread handle not inheritable
        FALSE,          // Set handle inheritance to FALSE
        0,              // No creation flags
        NULL,           // Use parent's environment block
        NULL,           // Use parent's starting directory
        &si,            // Pointer to STARTUPINFO structure
        &pi             // Pointer to PROCESS_INFORMATION structure
    );
    
    // Check if process creation was successful
    if (success) {
        printf("Process started successfully!\n");
        
        // Wait for the process to finish
        WaitForSingleObject(pi.hProcess, INFINITE);
        
        // Get the exit code
        DWORD exitCode;
        GetExitCodeProcess(pi.hProcess, &exitCode);
        printf("Process exited with code: %lu\n", exitCode);
        
        // Close process and thread handles
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
    } else {
        printf("Failed to start process. Error code: %lu\n", GetLastError());
    }
    
    return 0;
}
