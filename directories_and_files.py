#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path

# Constants
BYTES_PER_KB = 1024
INVALID_FILENAME_CHARS = '<>:"/\\|?*'


class FileManager:
    """A simple file manager for selecting, renaming, and deleting files."""

    def __init__(self):
        self.selected_files: list[Path] = []

    def get_directories(self, path: Path) -> list[Path]:
        """Get all directories in the given path."""
        try:
            return [d for d in sorted(path.iterdir()) if d.is_dir() and not d.is_symlink()]
        except (FileNotFoundError, PermissionError) as e:
            print(f"❌ Error accessing {path}: {e}")
            return []

    def get_files(self, path: Path) -> list[Path]:
        """Get all files in the given path."""
        try:
            return [f for f in sorted(path.glob("*")) if f.is_file() and not f.is_symlink()]
        except (FileNotFoundError, PermissionError) as e:
            print(f"❌ Error accessing {path}: {e}")
            return []

    def _display_directory_menu(self, current_path: Path, directories: list[Path]) -> str:
        """Display directory navigation menu and get user choice."""
        print("\n" + "=" * 60)
        print(f"📁 Current Directory: {current_path}")

        if directories:
            for i, directory in enumerate(directories, 1):
                print(f"  {i:2d}. {directory.name}")
        else:
            print("  📭 No subdirectories found")

        print("=" * 60)

        if directories:
            prompt = f"Choose: [y]es to use current | [1-{len(directories)}] to enter | [..] go up | [q]uit: "
        else:
            prompt = "Choose: [y]es to use current | [..] go up | [q]uit: "

        return input(prompt).strip().lower()

    def _handle_directory_choice(self, choice: str, current_path: Path, directories: list[Path]) -> Path | None:
        """Handle user's directory navigation choice."""
        if choice in ("y", "yes", ""):
            return current_path
        if choice in ("q", "quit"):
            return None
        if choice == "..":
            parent = current_path.parent
            if parent != current_path:  # Prevent going above root
                return parent
            print("⚠️  Already at root directory")
            return current_path
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(directories):
                return directories[idx]
            print(f"❌ Invalid choice. Please enter 1-{len(directories)}")
        else:
            print("❌ Invalid input. Please try again.")
        return current_path

    def choose_directory(self, start_path: Path) -> Path | None:
        """Navigate and choose a directory."""
        current_path = start_path

        while True:
            directories = self.get_directories(current_path)
            choice = self._display_directory_menu(current_path, directories)
            result = self._handle_directory_choice(choice, current_path, directories)

            if result is None:
                return None
            if result != current_path:
                current_path = result
            if choice in ("y", "yes", ""):
                return current_path

    def _display_file_menu(self, directory: Path, files: list[Path], selected_files: list[Path]) -> str:
        """Display file selection menu and get user choice."""
        print("\n" + "=" * 60)
        print(f"📁 Files in: {directory}")

        for i, file in enumerate(files, 1):
            marker = "✓" if file in selected_files else " "
            size = self.format_file_size(file.stat().st_size)
            print(f"  {marker} {i:2d}. {file.name} ({size})")

        if selected_files:
            print(f"\n✅ Selected: {len(selected_files)} files")

        print("=" * 60)
        return input(f"Select files [1-{len(files)}], [c]lear, [d]one, [q]uit: ").strip().lower()

    def _handle_file_choice(self, choice: str, files: list[Path], selected_files: list[Path]) -> bool:
        """Handle user's file selection choice. Returns True if should continue."""
        if choice in ("d", "done", ""):
            return False
        if choice in ("q", "quit"):
            selected_files.clear()
            return False
        if choice in ("c", "clear"):
            selected_files.clear()
            print("🗑️  Selection cleared")
            return True
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(files):
                file = files[idx]
                if file in selected_files:
                    selected_files.remove(file)
                    print(f"- Removed: {file.name}")
                else:
                    selected_files.append(file)
                    print(f"+ Added: {file.name}")
            else:
                print(f"❌ Invalid choice. Please enter 1-{len(files)}")
        else:
            print("❌ Invalid input. Please try again.")
        return True

    def choose_files(self, directory: Path) -> list[Path]:
        """Select multiple files from a directory."""
        files = self.get_files(directory)

        if not files:
            print(f"\n📭 No files found in {directory}")
            input("Press Enter to continue...")
            return []

        selected_files = []

        while True:
            choice = self._display_file_menu(directory, files, selected_files)
            should_continue = self._handle_file_choice(choice, files, selected_files)
            if not should_continue:
                break

        return selected_files

    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """Format file size in human-readable format."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < BYTES_PER_KB:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= BYTES_PER_KB
        return f"{size_bytes:.1f} TB"

    def _validate_filename(self, filename: str) -> bool:
        """Validate filename for invalid characters."""
        return not any(char in filename for char in INVALID_FILENAME_CHARS)

    def rename_files(self, files: list[Path]) -> None:
        """Rename selected files with user input."""
        if not files:
            return

        print(f"\n📝 Renaming {len(files)} files:")

        for file in files:
            print(f"\nCurrent: {file.name}")
            new_name = input("New name (Enter to skip): ").strip()

            if not new_name:
                print("⏭️  Skipped")
                continue

            if not self._validate_filename(new_name):
                print("❌ Invalid filename characters. Skipped.")
                continue

            new_path = file.parent / new_name

            if new_path.exists():
                print(f"❌ File '{new_name}' already exists. Skipped.")
                continue

            try:
                file.rename(new_path)
                print(f"✅ Renamed to: {new_name}")
            except (OSError, PermissionError) as e:
                print(f"❌ Error renaming {file.name}: {e}")

    def delete_files(self, files: list[Path]) -> None:
        """Delete selected files with confirmation."""
        if not files:
            return

        print(f"\n🗑️  Deleting {len(files)} files:")

        # Show all files to be deleted
        for file in files:
            size = self.format_file_size(file.stat().st_size)
            print(f"  - {file.name} ({size})")

        # Global confirmation
        confirm = input(f"\n⚠️  Delete ALL {len(files)} files? [y/N]: ").strip().lower()
        if confirm not in ("y", "yes"):
            print("❌ Deletion cancelled")
            return

        # Delete files
        deleted_count = 0
        try:
            for file in files:
                file.unlink()
                print(f"✅ Deleted: {file.name}")
                deleted_count += 1
        except (OSError, PermissionError) as e:
            print(f"❌ Error deleting {file.name}: {e}")

        print(f"\n🎉 Successfully deleted {deleted_count}/{len(files)} files")

    def _get_starting_directory(self) -> Path | None:
        """Get and validate the starting directory."""
        current_dir = Path.cwd()
        start_input = input(f"Enter starting directory [{current_dir}]: ").strip() or "."
        start_path = Path(start_input).resolve()

        if not start_path.exists():
            print(f"❌ Directory '{start_path}' does not exist")
            return None

        return start_path

    def _show_file_info(self, files: list[Path]) -> None:
        """Display information about selected files."""
        print("\n📊 File Information:")
        total_size = 0
        for file in files:
            size = file.stat().st_size
            total_size += size
            print(f"  {file.name}: {self.format_file_size(size)}")
        print(f"\n📏 Total size: {self.format_file_size(total_size)}")

    def _run_operations_menu(self, selected_files: list[Path]) -> None:
        """Run the operations menu for selected files."""
        while True:
            print(f"\n{'='*40}")
            print("Operations available:")
            print("  1. Rename files")
            print("  2. Delete files")
            print("  3. Show file info")
            print("  4. Quit")
            print("="*40)

            choice = input("Choose operation [1-4]: ").strip()

            if choice == "1":
                self.rename_files(selected_files)
            elif choice == "2":
                self.delete_files(selected_files)
                break  # Exit after deletion
            elif choice == "3":
                self._show_file_info(selected_files)
            elif choice in ("4", "q", "quit", ""):
                break
            else:
                print("❌ Invalid choice")

    def run(self) -> None:
        """Main program loop."""
        print("🚀 Welcome to File Manager!")

        try:
            # Get starting directory
            start_path = self._get_starting_directory()
            if not start_path:
                return

            # Choose directory
            chosen_dir = self.choose_directory(start_path)
            if not chosen_dir:
                print("👋 No directory selected. Goodbye!")
                return

            # Choose files
            selected_files = self.choose_files(chosen_dir)
            if not selected_files:
                print("👋 No files selected. Goodbye!")
                return

            print(f"\n🎯 Selected {len(selected_files)} files")

            # Run operations menu
            self._run_operations_menu(selected_files)

        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
        except (OSError, PermissionError) as e:
            print(f"❌ System error: {e}")


def main():
    """Entry point."""
    try:
        manager = FileManager()
        manager.run()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
