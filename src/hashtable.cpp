#include <assert.h>
#include <stdlib.h>     // calloc(), free()
#include "hashtable.h"


// n must be a power of 2
// initialize, creates the table
static void h_init(HTab *htab, size_t n) { //pointer to the hashtable struct we want to initialize, n-> number of buckets in the table
    assert(n > 0 && ((n - 1) & n) == 0); //n must be a power of two
    htab->tab = (HNode **)calloc(n, sizeof(HNode *)); //initialize as NULL
    htab->mask = n - 1;
    htab->size = 0;

    //creates an empty hash table skeleton 
}

// hashtable insertion
static void h_insert(HTab *htab, HNode *node) { //pointer to the hashtable and node that you want to add
    size_t pos = node->hcode & htab->mask; //compute bucket
    HNode *next = htab->tab[pos]; //gets the head of the bucket list 
    node->next = next; // link the node to the previous head
    htab->tab[pos] = node;
    htab->size++;
}

// hashtable look up subroutine.
// *htab is the pointer to the hashtable
//*key is the node containing the key that we are searching for 
// eq compares the two nodes
static HNode **h_lookup(HTab *htab, HNode *key, bool (*eq)(HNode *, HNode *)) {
    if (!htab->tab) {
        return NULL;
    } // check if table exists

    size_t pos = key->hcode & htab->mask; //which bucket to search
    HNode **from = &htab->tab[pos];     // incoming pointer to the target
    for (HNode *cur; (cur = *from) != NULL; from = &cur->next) {
        if (cur->hcode == key->hcode && eq(cur, key)) {
            return from;                // may be a node, may be a slot
        }
    }
    return NULL;
}

// remove a node from the chain
static HNode *h_detach(HTab *htab, HNode **from) {
    HNode *node = *from;    // the target node
    *from = node->next;     // update the incoming pointer to the target
    htab->size--;
    return node;
}

const size_t k_rehashing_work = 128;    // constant work

static void hm_help_rehashing(HMap *hmap) {
    size_t nwork = 0;
    while (nwork < k_rehashing_work && hmap->older.size > 0) {
        // find a non-empty slot
        HNode **from = &hmap->older.tab[hmap->migrate_pos];
        if (!*from) {
            hmap->migrate_pos++;
            continue;   // empty slot
        }
        // move the first list item to the newer table
        h_insert(&hmap->newer, h_detach(&hmap->older, from));
        nwork++;
    }
    // discard the old table if done
    if (hmap->older.size == 0 && hmap->older.tab) {
        free(hmap->older.tab);
        hmap->older = HTab();
    }
}

static void hm_trigger_rehashing(HMap *hmap) {
    assert(hmap->older.tab == NULL);
    // (newer, older) <- (new_table, newer)
    hmap->older = hmap->newer;
    h_init(&hmap->newer, (hmap->newer.mask + 1) * 2);
    hmap->migrate_pos = 0;
}

HNode *hm_lookup(HMap *hmap, HNode *key, bool (*eq)(HNode *, HNode *)) {
    hm_help_rehashing(hmap);
    HNode **from = h_lookup(&hmap->newer, key, eq);
    if (!from) {
        from = h_lookup(&hmap->older, key, eq);
    }
    return from ? *from : NULL;
}

const size_t k_max_load_factor = 8;

void hm_insert(HMap *hmap, HNode *node) {
    if (!hmap->newer.tab) {
        h_init(&hmap->newer, 4);    // initialize it if empty
    }
    h_insert(&hmap->newer, node);   // always insert to the newer table

    if (!hmap->older.tab) {         // check whether we need to rehash
        size_t shreshold = (hmap->newer.mask + 1) * k_max_load_factor;
        if (hmap->newer.size >= shreshold) {
            hm_trigger_rehashing(hmap);
        }
    }
    hm_help_rehashing(hmap);        // migrate some keys
}

HNode *hm_delete(HMap *hmap, HNode *key, bool (*eq)(HNode *, HNode *)) {
    hm_help_rehashing(hmap);
    if (HNode **from = h_lookup(&hmap->newer, key, eq)) {
        return h_detach(&hmap->newer, from);
    }
    if (HNode **from = h_lookup(&hmap->older, key, eq)) {
        return h_detach(&hmap->older, from);
    }
    return NULL;
}

void hm_clear(HMap *hmap) {
    free(hmap->newer.tab);
    free(hmap->older.tab);
    *hmap = HMap();
}

size_t hm_size(HMap *hmap) {
    return hmap->newer.size + hmap->older.size;
}
