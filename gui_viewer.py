import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import random
from collections import deque

class MemorySimulator:
    def __init__(self):
        self.MEMORY_SIZE = 65536
        self.PAGE_SIZE = 256
        self.TLB_SIZE = 16
        self.CACHE_SIZE = 64
        self.CACHE_LINE_SIZE = 8
        self.NUM_PAGES = self.MEMORY_SIZE // self.PAGE_SIZE
        
        self.reset_simulator()
    
    def reset_simulator(self):
        self.main_memory = bytearray([random.randint(0, 255) for _ in range(self.MEMORY_SIZE)])
        self.page_table = {}
        self.tlb = {}
        self.tlb_queue = deque()
        self.cache = [{'tag': -1, 'data': bytearray(self.CACHE_LINE_SIZE), 'valid': False, 'dirty': False} 
                     for _ in range(self.CACHE_SIZE)]
        self.stats = {
            'tlb_hits': 0, 'tlb_misses': 0, 'cache_hits': 0, 
            'cache_misses': 0, 'page_faults': 0, 'total_accesses': 0
        }

    def get_cache_components(self, physical_addr):
        offset_bits = (self.CACHE_LINE_SIZE - 1).bit_length()
        index_bits = (self.CACHE_SIZE - 1).bit_length()
        index = (physical_addr >> offset_bits) & (self.CACHE_SIZE - 1)
        tag = physical_addr >> (offset_bits + index_bits)
        offset = physical_addr & (self.CACHE_LINE_SIZE - 1)
        return tag, index, offset

    def handle_page_fault(self, page_num):
        self.stats['page_faults'] += 1
        frame_num = len(self.page_table) % self.NUM_PAGES
        start_addr = frame_num * self.PAGE_SIZE
        for i in range(self.PAGE_SIZE):
            self.main_memory[start_addr + i] = (page_num + i) % 256
        self.page_table[page_num] = frame_num
        return frame_num

    def update_tlb(self, page_num, frame_num):
        if page_num in self.tlb:
            return
        if len(self.tlb) >= self.TLB_SIZE:
            oldest_page = self.tlb_queue.popleft()
            del self.tlb[oldest_page]
        self.tlb[page_num] = frame_num
        self.tlb_queue.append(page_num)

    def access_cache(self, physical_addr):
        tag, index, offset = self.get_cache_components(physical_addr)
        cache_line = self.cache[index]
        
        if cache_line['valid'] and cache_line['tag'] == tag:
            self.stats['cache_hits'] += 1
            return cache_line['data'][offset], True
        else:
            self.stats['cache_misses'] += 1
            block_start = physical_addr & ~(self.CACHE_LINE_SIZE - 1)
            for i in range(self.CACHE_LINE_SIZE):
                cache_line['data'][i] = self.main_memory[block_start + i]
            cache_line['tag'] = tag
            cache_line['valid'] = True
            cache_line['dirty'] = False
            return cache_line['data'][offset], False

    def translate_address(self, virtual_addr):
        self.stats['total_accesses'] += 1
        
        page_num = (virtual_addr >> 8) & 0xFF
        offset = virtual_addr & 0xFF
        log_entries = []
        
        # TLB Check
        if page_num in self.tlb:
            frame_num = self.tlb[page_num]
            self.stats['tlb_hits'] += 1
            tlb_hit = True
            log_entries.append(f"✅TLB HIT: Page 0x{page_num:02X} -> Frame 0x{frame_num:02X}")
        else:
            self.stats['tlb_misses'] += 1
            tlb_hit = False
            log_entries.append(f"❌TLB MISS: Page 0x{page_num:02X}")
            
            # Page Table Check
            if page_num in self.page_table:
                frame_num = self.page_table[page_num]
                log_entries.append(f"✅PAGE TABLE HIT: Frame 0x{frame_num:02X}")
            else:
                frame_num = self.handle_page_fault(page_num)
                log_entries.append(f"🚨PAGE FAULT: Loading Page 0x{page_num:02X} to Frame 0x{frame_num:02X}")
            
            self.update_tlb(page_num, frame_num)
            log_entries.append(f"TLB UPDATE: Added (Page 0x{page_num:02X} -> Frame 0x{frame_num:02X})")
        
        # Physical Address
        physical_addr = (frame_num * self.PAGE_SIZE) + offset
        log_entries.append(f"Physical Address: 0x{physical_addr:04X}")
        
        # Cache Check
        value, cache_hit = self.access_cache(physical_addr)
        if cache_hit:
            log_entries.append(f"✅CACHE HIT: Value = {value}")
        else:
            log_entries.append(f"❌CACHE MISS: Loaded from memory, Value = {value}")
        
        result = {
            'virtual_addr': virtual_addr,
            'physical_addr': physical_addr,
            'value': value,
            'page_num': page_num,
            'frame_num': frame_num,
            'tlb_hit': tlb_hit,
            'cache_hit': cache_hit,
            'log': log_entries
        }
        
        return result

class MemorySimulatorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Memory Management Simulator")
        self.root.geometry("900x700")
        
        self.simulator = MemorySimulator()
        self.setup_gui()
        
    def setup_gui(self):
        # Create notebook (tab controller)
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create tabs
        control_frame = ttk.Frame(notebook)
        tlb_frame = ttk.Frame(notebook)
        page_table_frame = ttk.Frame(notebook)
        cache_frame = ttk.Frame(notebook)
        stats_frame = ttk.Frame(notebook)
        
        notebook.add(control_frame, text="Control Panel")
        notebook.add(tlb_frame, text="TLB")
        notebook.add(page_table_frame, text="Page Table")
        notebook.add(cache_frame, text="Cache")
        notebook.add(stats_frame, text="Statistics")
        
        # Setup each tab
        self.setup_control_tab(control_frame)
        self.setup_tlb_tab(tlb_frame)
        self.setup_page_table_tab(page_table_frame)
        self.setup_cache_tab(cache_frame)
        self.setup_stats_tab(stats_frame)
        
    def setup_control_tab(self, parent):
        # Address input section
        addr_frame = ttk.LabelFrame(parent, text="Address Input")
        addr_frame.pack(fill='x', padx=10, pady=5)
        
        input_frame = ttk.Frame(addr_frame)
        input_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(input_frame, text="Virtual Address:").pack(side='left', padx=5)
        
        self.addr_var = tk.StringVar()
        addr_entry = ttk.Entry(input_frame, textvariable=self.addr_var, width=15)
        addr_entry.pack(side='left', padx=5)
        
        self.addr_format = tk.StringVar(value="hex")
        ttk.Radiobutton(input_frame, text="Hex", variable=self.addr_format, value="hex").pack(side='left', padx=5)
        ttk.Radiobutton(input_frame, text="Decimal", variable=self.addr_format, value="decimal").pack(side='left', padx=5)
        
        # Buttons
        btn_frame = ttk.Frame(addr_frame)
        btn_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(btn_frame, text="Process Address", command=self.process_address).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="Reset Simulator", command=self.reset_simulator).pack(side='left', padx=2)
        
        # Log display
        log_frame = ttk.LabelFrame(parent, text="Processing Log")
        log_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=80)
        self.log_text.pack(fill='both', expand=True, padx=5, pady=5)
        self.log_text.config(state='disabled')
        
    def setup_tlb_tab(self, parent):
        tlb_frame = ttk.Frame(parent)
        tlb_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # TLB table
        columns = ('page', 'frame')
        self.tlb_tree = ttk.Treeview(tlb_frame, columns=columns, show='headings', height=10)
        
        self.tlb_tree.heading('page', text='Page Number')
        self.tlb_tree.heading('frame', text='Frame Number')
        
        self.tlb_tree.column('page', width=100)
        self.tlb_tree.column('frame', width=100)
        
        self.tlb_tree.pack(fill='both', expand=True)
        
    def setup_page_table_tab(self, parent):
        page_table_frame = ttk.Frame(parent)
        page_table_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Page Table table
        columns = ('page', 'frame', 'status')
        self.page_table_tree = ttk.Treeview(page_table_frame, columns=columns, show='headings', height=15)
        
        self.page_table_tree.heading('page', text='Page Number')
        self.page_table_tree.heading('frame', text='Frame Number')
        self.page_table_tree.heading('status', text='Status')
        
        self.page_table_tree.column('page', width=100)
        self.page_table_tree.column('frame', width=100)
        self.page_table_tree.column('status', width=100)
        
        scrollbar = ttk.Scrollbar(page_table_frame, orient='vertical', command=self.page_table_tree.yview)
        self.page_table_tree.configure(yscrollcommand=scrollbar.set)
        
        self.page_table_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
    def setup_cache_tab(self, parent):
        cache_frame = ttk.Frame(parent)
        cache_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Cache table
        columns = ('index', 'valid', 'tag', 'data')
        self.cache_tree = ttk.Treeview(cache_frame, columns=columns, show='headings', height=15)
        
        self.cache_tree.heading('index', text='Index')
        self.cache_tree.heading('valid', text='Valid')
        self.cache_tree.heading('tag', text='Tag')
        self.cache_tree.heading('data', text='Data Preview')
        
        for col in columns:
            self.cache_tree.column(col, width=100)
        
        self.cache_tree.pack(fill='both', expand=True)
        
    def setup_stats_tab(self, parent):
        stats_frame = ttk.Frame(parent)
        stats_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.stats_text = scrolledtext.ScrolledText(stats_frame, height=20, width=60)
        self.stats_text.pack(fill='both', expand=True)
        self.stats_text.config(state='disabled')
    
    def process_address(self):
        address_str = self.addr_var.get().strip()
        if not address_str:
            messagebox.showerror("Error", "Please enter an address")
            return
            
        if self.addr_format.get() == "hex" and not address_str.startswith("0x"):
            address_str = "0x" + address_str
            
        try:
            if address_str.lower().startswith('0x'):
                virtual_addr = int(address_str, 16)
            else:
                virtual_addr = int(address_str)
                
            if virtual_addr < 0 or virtual_addr > 0xFFFF:
                messagebox.showerror("Error", "Address out of range (0x0000-0xFFFF)")
                return
                
            result = self.simulator.translate_address(virtual_addr)
            self.update_display(result)
            
        except ValueError:
            messagebox.showerror("Error", "Invalid address format")
    
    def reset_simulator(self):
        self.simulator.reset_simulator()
        self.addr_var.set("")
        self.update_display(None)
        self.log_message("Simulator reset successfully!")
    
    def update_display(self, result):
        # Update log
        if result:
            self.log_text.config(state='normal')
            self.log_text.delete(1.0, tk.END)
            for log_entry in result['log']:
                self.log_text.insert(tk.END, log_entry + '\n')
            self.log_text.config(state='disabled')
        
        # Update TLB tab
        self.tlb_tree.delete(*self.tlb_tree.get_children())
        for page, frame in self.simulator.tlb.items():
            self.tlb_tree.insert('', 'end', values=(f"0x{page:02X}", f"0x{frame:02X}"))
        
        # Update Page Table tab
        self.page_table_tree.delete(*self.page_table_tree.get_children())
        for page, frame in self.simulator.page_table.items():
            status = "USED" if result and page == result['page_num'] else "LOADED"
            self.page_table_tree.insert('', 'end', values=(
                f"0x{page:02X}", 
                f"0x{frame:02X}", 
                status
            ))
        
        # Update Cache tab
        self.cache_tree.delete(*self.cache_tree.get_children())
        for i, line in enumerate(self.simulator.cache):
            if line['valid']:
                data_preview = ' '.join(f"{b:02X}" for b in line['data'][:3])
                self.cache_tree.insert('', 'end', values=(
                    str(i), 
                    "YES", 
                    f"0x{line['tag']:02X}", 
                    data_preview + "..."
                ))
        
        # Update Statistics tab
        stats = self.simulator.stats
        tlb_total = stats['tlb_hits'] + stats['tlb_misses']
        cache_total = stats['cache_hits'] + stats['cache_misses']
        
        tlb_hit_rate = (stats['tlb_hits'] / tlb_total * 100) if tlb_total > 0 else 0
        cache_hit_rate = (stats['cache_hits'] / cache_total * 100) if cache_total > 0 else 0
        
        stats_text = f"""MEMORY MANAGEMENT STATISTICS

TLB Performance:
✅Hits: {stats['tlb_hits']}
❌Misses: {stats['tlb_misses']}
📈Hit Rate: {tlb_hit_rate:.1f}%

Cache Performance:
✅Hits: {stats['cache_hits']}
❌Misses: {stats['cache_misses']}
📈Hit Rate: {cache_hit_rate:.1f}%

System Events:
🚨Page Faults: {stats['page_faults']}
🔢Total Accesses: {stats['total_accesses']}

Page Table:
📖Total Pages: {len(self.simulator.page_table)}
"""
        
        self.stats_text.config(state='normal')
        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(tk.END, stats_text)
        self.stats_text.config(state='disabled')
    
    def log_message(self, message):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + '\n')
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')

if __name__ == "__main__":
    root = tk.Tk()
    app = MemorySimulatorGUI(root)
    root.mainloop()