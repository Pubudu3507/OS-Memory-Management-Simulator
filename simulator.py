import random
from collections import deque

# Configuration
MEMORY_SIZE = 65536      # 64 KB RAM
PAGE_SIZE = 256          # 256 bytes per page
TLB_SIZE = 16            # 16 entry TLB
CACHE_SIZE = 64          # 64 cache lines
CACHE_LINE_SIZE = 8      # 8 bytes per cache line
NUM_PAGES = MEMORY_SIZE // PAGE_SIZE

# Data Structures
main_memory = bytearray([random.randint(0, 255) for _ in range(MEMORY_SIZE)])
page_table = {}          # {page_num: frame_num}
tlb = {}                 # {page_num: frame_num}
tlb_queue = deque()      # For FIFO replacement

# Cache: list of {tag, data, valid, dirty}
cache = [{'tag': -1, 'data': bytearray(CACHE_LINE_SIZE), 'valid': False, 'dirty': False} 
         for _ in range(CACHE_SIZE)]

# Statistics
stats = {
    'tlb_hits': 0,
    'tlb_misses': 0,
    'cache_hits': 0,
    'cache_misses': 0,
    'page_faults': 0,
    'total_accesses': 0
}

# Cache Calculations
CACHE_OFFSET_BITS = (CACHE_LINE_SIZE - 1).bit_length()
CACHE_INDEX_BITS = (CACHE_SIZE - 1).bit_length()
CACHE_TAG_BITS = 16 - CACHE_INDEX_BITS - CACHE_OFFSET_BITS

def get_cache_components(physical_addr):
    """Extract tag, index, and offset from physical address"""
    index = (physical_addr >> CACHE_OFFSET_BITS) & (CACHE_SIZE - 1)
    tag = physical_addr >> (CACHE_OFFSET_BITS + CACHE_INDEX_BITS)
    offset = physical_addr & (CACHE_LINE_SIZE - 1)
    return tag, index, offset

# Core Functions
def handle_page_fault(page_num):
    """Simulate loading a page from disk into memory"""
    global stats
    stats['page_faults'] += 1
    
    # Find a free frame
    frame_num = len(page_table) % NUM_PAGES
    
    # Load data (simulate with pattern)
    start_addr = frame_num * PAGE_SIZE
    for i in range(PAGE_SIZE):
        main_memory[start_addr + i] = (page_num + i) % 256
    
    page_table[page_num] = frame_num
    return frame_num

def update_tlb(page_num, frame_num):
    """Update TLB with FIFO replacement policy"""
    if page_num in tlb:
        return
    
    if len(tlb) >= TLB_SIZE:
        oldest_page = tlb_queue.popleft()
        del tlb[oldest_page]
    
    tlb[page_num] = frame_num
    tlb_queue.append(page_num)

def access_cache(physical_addr):
    """Access cache, return value and whether it was a hit"""
    global stats
    
    tag, index, offset = get_cache_components(physical_addr)
    cache_line = cache[index]
    
    if cache_line['valid'] and cache_line['tag'] == tag:
        stats['cache_hits'] += 1
        return cache_line['data'][offset], True
    else:
        stats['cache_misses'] += 1
        
        # Read entire block from main memory
        block_start = physical_addr & ~(CACHE_LINE_SIZE - 1)
        for i in range(CACHE_LINE_SIZE):
            cache_line['data'][i] = main_memory[block_start + i]
        
        cache_line['tag'] = tag
        cache_line['valid'] = True
        cache_line['dirty'] = False
        
        return cache_line['data'][offset], False

def translate_address(virtual_addr):
    """Translate virtual address through memory hierarchy"""
    global stats
    stats['total_accesses'] += 1
    
    # Extract page number and offset
    page_num = (virtual_addr >> 8) & 0xFF
    offset = virtual_addr & 0xFF
    
    log_entries = []
    
    # Step 1: Check TLB
    if page_num in tlb:
        frame_num = tlb[page_num]
        stats['tlb_hits'] += 1
        tlb_hit = True
        log_entries.append(f"TLB HIT: Page 0x{page_num:02X} -> Frame 0x{frame_num:02X}")
    else:
        stats['tlb_misses'] += 1
        tlb_hit = False
        log_entries.append(f"TLB MISS: Page 0x{page_num:02X}")
        
        # Step 2: Check Page Table
        if page_num in page_table:
            frame_num = page_table[page_num]
            log_entries.append(f"PAGE TABLE HIT: Frame 0x{frame_num:02X}")
        else:
            frame_num = handle_page_fault(page_num)
            log_entries.append(f"PAGE FAULT: Loading Page 0x{page_num:02X} to Frame 0x{frame_num:02X}")
        
        update_tlb(page_num, frame_num)
        log_entries.append(f"TLB UPDATE: Added (Page 0x{page_num:02X} -> Frame 0x{frame_num:02X})")
    
    # Calculate physical address
    physical_addr = (frame_num * PAGE_SIZE) + offset
    log_entries.append(f"Physical Address: 0x{physical_addr:04X}")
    
    # Step 4: Check Cache
    value, cache_hit = access_cache(physical_addr)
    if cache_hit:
        log_entries.append(f"CACHE HIT: Value = {value}")
    else:
        log_entries.append(f"CACHE MISS: Loaded from memory, Value = {value}")
    
    return {
        'virtual_addr': virtual_addr,
        'physical_addr': physical_addr,
        'value': value,
        'page_num': page_num,
        'frame_num': frame_num,
        'tlb_hit': tlb_hit,
        'cache_hit': cache_hit,
        'log': log_entries
    }

# Snapshot Functions
def get_tlb_snapshot():
    """Return current TLB state"""
    return dict(tlb)

def get_cache_snapshot():
    """Return current cache state"""
    return cache

def get_page_table_snapshot():
    """Return current page table state"""
    return dict(page_table)

def get_stats():
    """Return current statistics"""
    return stats.copy()

def reset_simulator():
    """Reset all simulator state"""
    global main_memory, page_table, tlb, tlb_queue, cache, stats
    
    main_memory = bytearray([random.randint(0, 255) for _ in range(MEMORY_SIZE)])
    page_table = {}
    tlb = {}
    tlb_queue = deque()
    cache = [{'tag': -1, 'data': bytearray(CACHE_LINE_SIZE), 'valid': False, 'dirty': False} 
             for _ in range(CACHE_SIZE)]
    stats = {
        'tlb_hits': 0, 'tlb_misses': 0, 'cache_hits': 0, 
        'cache_misses': 0, 'page_faults': 0, 'total_accesses': 0
    }