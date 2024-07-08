import os
import shutil
import pydicom
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

def create_directory_if_not_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)


def get_modality_frame_of_reference_and_series_description(file_path):
    'Returns key tags for a specified dcm file.'
    
    print(f'Reading: {file_path}')
    dataset = pydicom.dcmread(file_path, stop_before_pixels=True)
    # print(dataset)
    modality = dataset.Modality
    
    try:
        if modality == 'RTSTRUCT':
            # FrameOfReferenceUID is at difference location for RTSTRUCT then for other modalities
            frame_of_reference_uid = dataset.ReferencedFrameOfReferenceSequence[0].FrameOfReferenceUID
        else:
            frame_of_reference_uid = dataset.FrameOfReferenceUID
    except AttributeError:
        frame_of_reference_uid = 'NoFrameOfReferenceUID'
        
    series_description = getattr(dataset, 'SeriesDescription', 'NoSeriesDescription')
    if modality == 'RTPLAN':
        # Add approval status info to series description of RTPLAN
        try:
            series_description = series_description + f' ({dataset.ApprovalStatus})'
        except AttributeError:
            series_description = series_description + f' (NoApprovalStatus)'
        
    return modality, frame_of_reference_uid, series_description


def classify_dicom_files(source_folder):
    'Classifies dcm files in a dictionary by using tags specified in get_etc function above.'
    
    # Dictionary to hold the structure
    structure = {}

    # Walk through the source folder
    for root, _, files in os.walk(source_folder):
        for file in files:
            if file.lower().endswith('.dcm'):
                file_path = os.path.join(root, file)
                try:
                    modality, frame_of_reference_uid, series_description = get_modality_frame_of_reference_and_series_description(file_path)
                except AttributeError as e:
                    print(f"Skipping file {file_path} due to missing attribute: {e}")
                    continue
                
                # Populate the structure dictionary
                if modality not in structure:
                    structure[modality] = {}
                if frame_of_reference_uid not in structure[modality]:
                    structure[modality][frame_of_reference_uid] = {}
                if series_description not in structure[modality][frame_of_reference_uid]:
                    structure[modality][frame_of_reference_uid][series_description] = []
                structure[modality][frame_of_reference_uid][series_description].append(file_path)

    return structure


def populate_tree(tree, structure):
    'Recursively inserts the retrieved information into a tree view.'
    for modality, frame_dict in structure.items():
        modality_node = tree.insert('', 'end', text=modality, values=('Modality',))
        for frame_of_reference_uid, series_dict in frame_dict.items():
            frame_node = tree.insert(modality_node, 'end', text=frame_of_reference_uid, values=('Frame of Reference UID',))
            for series_description, files in series_dict.items():
                series_node = tree.insert(frame_node, 'end', text=series_description, values=(f'Series Description ({len(files)} files)',))
                for file in files:
                    tree.insert(series_node, 'end', text=os.path.basename(file), values=(file,))


class DICOMSortApp(tk.Tk):
    'Class initializes the main window and its widget.'
    def __init__(self):
        super().__init__()

        self.title("DICOM Sort")
        self.geometry("800x600")

        self.folder_path = tk.StringVar()

        self.create_widgets()

    def create_widgets(self):
        'Sets up the entry for folder path and load button, and tree view.'
        frame = ttk.Frame(self)
        frame.pack(padx=10, pady=10, fill=tk.X)

        label = ttk.Label(frame, text="Click Load to Select Folder with DICOM Files:")
        label.pack(side=tk.LEFT, padx=(0, 5))

        # entry = ttk.Entry(frame, textvariable=self.folder_path, width=50)
        # entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        load_button = ttk.Button(frame, text="Load", command=self.browse_and_load_dicom_files)
        load_button.pack(side=tk.LEFT, padx=(5, 0))
        
        label = ttk.Label(frame, text="Hold down Ctrl to Select Files and Choose Target Folder:")
        label.pack(side=tk.LEFT, padx=(25, 5))

        copy_button = ttk.Button(frame, text="Copy Selection", command=self.copy_selected_files)
        copy_button.pack(side=tk.LEFT, padx=(5, 0))
    

        self.tree = ttk.Treeview(self, selectmode='extended')
        self.tree["columns"] = ("Info",)
        self.tree.column("#0", width=300, minwidth=150)
        self.tree.column("Info", width=400, minwidth=200)
        self.tree.heading("#0", text="Name", anchor=tk.W)
        self.tree.heading("Info", text="Information", anchor=tk.W)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind('<Double-1>', self.on_tree_item_double_click)

    def browse_and_load_dicom_files(self):
        'Browses for a folder and loads the DICOM files.'
        folder_selected = filedialog.askdirectory()
        if not folder_selected:
            messagebox.showerror("Error", "Please select a folder.")
            return

        self.folder_path.set(folder_selected)
        folder = self.folder_path.get()
        self.tree.delete(*self.tree.get_children())  # Clear existing tree view
        try:
            structure = classify_dicom_files(folder)
            populate_tree(self.tree, structure)
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")

    def copy_selected_files(self):
        'Copies the selected files to a specified folder.'
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showerror("Error", "No items selected.")
            return
        
        target_folder = filedialog.askdirectory()
        if not target_folder:
            messagebox.showerror("Error", "No target folder selected.")
            return

        files_to_copy = []
        for item in selected_items:
            self.collect_files(item, files_to_copy)

        for file_path in files_to_copy:
            if os.path.isfile(file_path):
                shutil.copy(file_path, target_folder)
        
        messagebox.showinfo("Success", "Selected files have been copied.")

    def collect_files(self, item, files_to_copy):
        'Recursively collects files from the selected items and their children.'
        children = self.tree.get_children(item)
        if not children:  # It's a file
            file_path = self.tree.item(item, 'values')[0]
            files_to_copy.append(file_path)
        else:  # It's a folder-like item
            for child in children:
                self.collect_files(child, files_to_copy)

    def on_tree_item_double_click(self, event):
        'Shows detailed dcm info about file upon double-click.'
        item = self.tree.selection()[0]
        file_path = self.tree.item(item, 'values')[0]
        if file_path:
            self.show_dicom_details(file_path)

    def show_dicom_details(self, file_path):
        'Opens a new window and displays all elements of the DICOM dataset, including their tags, names, and values.'
        dataset = pydicom.dcmread(file_path)
        info_window = tk.Toplevel(self)
        info_window.title(f"Details for {os.path.basename(file_path)}")

        info_text = tk.Text(info_window, wrap='word', height=30, width=100)
        info_text.pack(expand=True, fill='both')

        # Display all dataset elements
        for elem in dataset:
            tag = elem.tag
            try:
                value = elem.value
            except AttributeError:
                value = 'N/A'
            info_text.insert(tk.END, f"Tag: {tag}\n")
            info_text.insert(tk.END, f"Name: {elem.name}\n")
            info_text.insert(tk.END, f"Value: {value}\n\n")
        info_text.config(state=tk.DISABLED)

if __name__ == "__main__":
    app = DICOMSortApp()
    app.mainloop()
