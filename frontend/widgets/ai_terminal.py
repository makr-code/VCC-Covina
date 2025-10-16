"""
AITerminal Widget - Phase 2: UI Components

AI-powered terminal interface with:
- Command input with history (↑↓ navigation)
- Output area (scrollable, syntax highlighting ready)
- Auto-complete support (placeholder)
- Command history tracking
- Backend AI integration (placeholder for now)

Author: Covina Development Team
Version: 4.0.0 (Frontend Modernization - Phase 2)
Date: 14.10.2025, 10:00 Uhr
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable, List, Dict, Any
from datetime import datetime
from frontend.core.event_bus import EventType


class CommandHistory:
    """Manages command history with navigation."""
    
    def __init__(self, max_size: int = 100):
        self._history: List[str] = []
        self._max_size = max_size
        self._current_index = -1
    
    def add(self, command: str):
        """Add command to history."""
        if command and (not self._history or self._history[-1] != command):
            self._history.append(command)
            if len(self._history) > self._max_size:
                self._history.pop(0)
        self._current_index = len(self._history)
    
    def previous(self) -> Optional[str]:
        """Get previous command (↑)."""
        if not self._history:
            return None
        
        if self._current_index > 0:
            self._current_index -= 1
        return self._history[self._current_index]
    
    def next(self) -> Optional[str]:
        """Get next command (↓)."""
        if not self._history:
            return None
        
        if self._current_index < len(self._history) - 1:
            self._current_index += 1
            return self._history[self._current_index]
        else:
            self._current_index = len(self._history)
            return ""
    
    def reset_position(self):
        """Reset navigation position."""
        self._current_index = len(self._history)
    
    def get_all(self) -> List[str]:
        """Get all commands."""
        return self._history.copy()
    
    def clear(self):
        """Clear history."""
        self._history.clear()
        self._current_index = -1


class CommandInput(ttk.Frame):
    """Command input field with history navigation."""
    
    def __init__(
        self,
        parent,
        on_submit: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        self._on_submit = on_submit
        self._history = CommandHistory()
        self._build_ui()
    
    def _build_ui(self):
        """Build the input UI."""
        # Prompt label
        prompt_label = ttk.Label(
            self,
            text=">>>",
            font=("Consolas", 10, "bold"),
            foreground="#00AA00"
        )
        prompt_label.pack(side="left", padx=(5, 5))
        
        # Input entry
        self._entry = ttk.Entry(
            self,
            font=("Consolas", 10)
        )
        self._entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        # Bind events
        self._entry.bind("<Return>", self._on_return)
        self._entry.bind("<Up>", self._on_up)
        self._entry.bind("<Down>", self._on_down)
        self._entry.bind("<Tab>", self._on_tab)
    
    def _on_return(self, event):
        """Handle Return key (submit command)."""
        command = self._entry.get().strip()
        if command:
            # Add to history
            self._history.add(command)
            
            # Execute callback
            if self._on_submit:
                self._on_submit(command)
            
            # Clear input
            self._entry.delete(0, tk.END)
    
    def _on_up(self, event):
        """Handle Up arrow (previous command)."""
        prev = self._history.previous()
        if prev is not None:
            self._entry.delete(0, tk.END)
            self._entry.insert(0, prev)
        return "break"  # Prevent default behavior
    
    def _on_down(self, event):
        """Handle Down arrow (next command)."""
        next_cmd = self._history.next()
        if next_cmd is not None:
            self._entry.delete(0, tk.END)
            self._entry.insert(0, next_cmd)
        return "break"
    
    def _on_tab(self, event):
        """Handle Tab key (auto-complete - placeholder)."""
        # TODO: Implement auto-complete
        return "break"
    
    def focus(self):
        """Set focus to input field."""
        self._entry.focus_set()
    
    def clear(self):
        """Clear input field."""
        self._entry.delete(0, tk.END)
    
    def get_history(self) -> List[str]:
        """Get command history."""
        return self._history.get_all()
    
    def clear_history(self):
        """Clear command history."""
        self._history.clear()


class OutputArea(tk.Frame):
    """Scrollable output area for terminal output."""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._build_ui()
    
    def _build_ui(self):
        """Build the output area UI."""
        # Text widget with scrollbar
        self._text = tk.Text(
            self,
            wrap="word",
            font=("Consolas", 10),
            bg="#1E1E1E",
            fg="#D4D4D4",
            insertbackground="white",
            state="disabled",
            height=10
        )
        
        scrollbar = ttk.Scrollbar(
            self,
            orient="vertical",
            command=self._text.yview
        )
        
        self._text.configure(yscrollcommand=scrollbar.set)
        
        # Pack widgets
        scrollbar.pack(side="right", fill="y")
        self._text.pack(side="left", fill="both", expand=True)
        
        # Configure tags for colored output
        self._text.tag_config("command", foreground="#569CD6", font=("Consolas", 10, "bold"))
        self._text.tag_config("output", foreground="#D4D4D4")
        self._text.tag_config("error", foreground="#F44747")
        self._text.tag_config("success", foreground="#4EC9B0")
        self._text.tag_config("info", foreground="#9CDCFE")
        self._text.tag_config("timestamp", foreground="#858585", font=("Consolas", 9))
    
    def append_command(self, command: str):
        """Append command to output."""
        self._append_text(f"\n>>> {command}\n", "command")
    
    def append_output(self, text: str, output_type: str = "output"):
        """
        Append output text.
        
        Args:
            text: Output text
            output_type: Type of output (output, error, success, info)
        """
        self._append_text(text + "\n", output_type)
    
    def append_error(self, error: str):
        """Append error message."""
        self._append_text(f"ERROR: {error}\n", "error")
    
    def append_success(self, message: str):
        """Append success message."""
        self._append_text(f"✓ {message}\n", "success")
    
    def append_info(self, message: str):
        """Append info message."""
        self._append_text(f"ℹ {message}\n", "info")
    
    def _append_text(self, text: str, tag: str = "output"):
        """Append text with tag."""
        self._text.config(state="normal")
        
        # Add timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._text.insert(tk.END, f"[{timestamp}] ", "timestamp")
        
        # Add text
        self._text.insert(tk.END, text, tag)
        
        # Auto-scroll to bottom
        self._text.see(tk.END)
        
        self._text.config(state="disabled")
    
    def clear(self):
        """Clear output area."""
        self._text.config(state="normal")
        self._text.delete("1.0", tk.END)
        self._text.config(state="disabled")
    
    def get_text(self) -> str:
        """Get all text."""
        return self._text.get("1.0", tk.END)


class AITerminal(ttk.Frame):
    """
    AI-powered terminal interface.
    
    Features:
    - Command input with history (↑↓ navigation)
    - Output area (scrollable, colored output)
    - Auto-complete support (placeholder)
    - Command history tracking
    - Backend AI integration (placeholder)
    - Height: 200px (resizable: 100-400px)
    
    Example:
        terminal = AITerminal(
            parent,
            event_bus,
            on_command=lambda cmd: print(f"Execute: {cmd}")
        )
        terminal.pack(side="bottom", fill="x")
        
        # Execute command
        terminal.execute_command("help")
        
        # Add output
        terminal.append_output("Command executed successfully", "success")
    """
    
    def __init__(
        self,
        parent,
        event_bus,
        on_command: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        self._event_bus = event_bus
        self._on_command = on_command
        self._collapsed = False
        
        self.config(height=200, relief="solid", borderwidth=1)
        self.pack_propagate(False)
        
        self._build_ui()
        self._register_built_in_commands()
    
    def _build_ui(self):
        """Build the terminal UI."""
        # Header with collapse button
        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x", padx=5, pady=5)
        
        # Title
        title_label = ttk.Label(
            header_frame,
            text="🤖 AI Terminal",
            font=("Segoe UI", 10, "bold")
        )
        title_label.pack(side="left")
        
        # Status indicator
        self._status_label = ttk.Label(
            header_frame,
            text="⚪ Ready",
            font=("Segoe UI", 9)
        )
        self._status_label.pack(side="left", padx=10)
        
        # Collapse button
        self._collapse_btn = ttk.Button(
            header_frame,
            text="▼",
            width=3,
            command=self.toggle_collapse
        )
        self._collapse_btn.pack(side="right")
        
        # Content container
        self._content_frame = ttk.Frame(self)
        self._content_frame.pack(fill="both", expand=True, padx=5, pady=(0, 5))
        
        # Output area
        self._output = OutputArea(self._content_frame)
        self._output.pack(fill="both", expand=True, pady=(0, 5))
        
        # Input area
        self._input = CommandInput(
            self._content_frame,
            on_submit=self._handle_command
        )
        self._input.pack(fill="x")
        
        # Welcome message
        self._output.append_info("AI Terminal initialized. Type 'help' for commands.")
    
    def _register_built_in_commands(self):
        """Register built-in terminal commands."""
        self._built_in_commands = {
            "help": self._cmd_help,
            "clear": self._cmd_clear,
            "history": self._cmd_history,
            "status": self._cmd_status,
        }
    
    def _handle_command(self, command: str):
        """Handle command submission."""
        # Show command in output
        self._output.append_command(command)
        
        # Parse command
        parts = command.split()
        if not parts:
            return
        
        cmd = parts[0].lower()
        args = parts[1:]
        
        # Check built-in commands
        if cmd in self._built_in_commands:
            self._built_in_commands[cmd](args)
        else:
            # Execute custom command
            self._execute_command(command)
    
    def _execute_command(self, command: str):
        """Execute custom command."""
        # Emit event
        if self._event_bus:
            self._event_bus.emit_sync(EventType.AI_COMMAND_SUBMITTED, {"command": command})
        
        # Call callback
        if self._on_command:
            try:
                result = self._on_command(command)
                if result:
                    self._output.append_output(str(result))
            except Exception as e:
                self._output.append_error(str(e))
        else:
            self._output.append_info(f"Command '{command}' received (no handler registered)")
    
    # Built-in Commands
    
    def _cmd_help(self, args: List[str]):
        """Show help."""
        help_text = """
Available Commands:
  help     - Show this help message
  clear    - Clear terminal output
  history  - Show command history
  status   - Show terminal status

AI Commands (examples):
  analyze <file>         - Analyze a document
  search <query>         - Search documents
  summarize <doc_id>     - Summarize a document
"""
        self._output.append_info(help_text.strip())
    
    def _cmd_clear(self, args: List[str]):
        """Clear output."""
        self._output.clear()
        self._output.append_info("Terminal cleared.")
    
    def _cmd_history(self, args: List[str]):
        """Show command history."""
        history = self._input.get_history()
        if history:
            self._output.append_info("Command History:")
            for i, cmd in enumerate(history[-10:], 1):
                self._output.append_output(f"  {i}. {cmd}")
        else:
            self._output.append_info("No command history.")
    
    def _cmd_status(self, args: List[str]):
        """Show status."""
        self._output.append_success("Terminal is running normally.")
        self._output.append_info(f"Commands in history: {len(self._input.get_history())}")
    
    # Public Methods
    
    def execute_command(self, command: str):
        """Programmatically execute a command."""
        self._handle_command(command)
    
    def append_output(self, text: str, output_type: str = "output"):
        """Append output text."""
        self._output.append_output(text, output_type)
    
    def append_error(self, error: str):
        """Append error message."""
        self._output.append_error(error)
    
    def append_success(self, message: str):
        """Append success message."""
        self._output.append_success(message)
    
    def append_info(self, message: str):
        """Append info message."""
        self._output.append_info(message)
    
    def clear_output(self):
        """Clear output area."""
        self._output.clear()
    
    def clear_history(self):
        """Clear command history."""
        self._input.clear_history()
    
    def set_status(self, status: str, color: str = "black"):
        """Set status indicator."""
        icon = "🟢" if "ready" in status.lower() or "ok" in status.lower() else "⚪"
        self._status_label.config(text=f"{icon} {status}", foreground=color)
    
    def toggle_collapse(self):
        """Toggle terminal collapse state."""
        self._collapsed = not self._collapsed
        
        if self._collapsed:
            # Collapsed: Hide content, minimize height
            self._content_frame.pack_forget()
            self._collapse_btn.config(text="▲")
            self.config(height=40)
        else:
            # Expanded: Show content, restore height
            self._content_frame.pack(fill="both", expand=True, padx=5, pady=(0, 5))
            self._collapse_btn.config(text="▼")
            self.config(height=200)
        
        # Emit event
        if self._event_bus:
            self._event_bus.emit_sync(
                "AI_TERMINAL_TOGGLED",
                {"collapsed": self._collapsed}
            )
    
    def is_collapsed(self) -> bool:
        """Check if terminal is collapsed."""
        return self._collapsed
    
    def focus(self):
        """Set focus to input field."""
        self._input.focus()


# Export
__all__ = [
    "AITerminal",
    "CommandInput",
    "OutputArea",
    "CommandHistory",
]
