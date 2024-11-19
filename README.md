# Practica2AC
## FASE 2
### TO-DO
* [Modificar bpred.h](#bpredh)
* [Modificar bpred.c](#bpredc)
* [Modificar sim-outorder.c](#sim-outorderc)

- Explicacion de cada parámetro del struct `2level`
```c
struct {
    int l1size; //-> Mida `GBHR` - Si es 4 tendremos capacidad para almacenar 4 bits de historia
    int l2size; //-> Mida Taula `PHT` - Si es 256, tendremos esa capacidad, por tanto 256 entradas con contadores de 2 bits
    int shift_width; //-> amount of history in level-1 shift regs - Si es 4 GBHR se actualizara desplazando 4 bits
    int xor; //-> resultado para acceder a la PHT(según PC y GBHR) - indica si se usa xor o no
    int *shiftregs; //-> puntero hacia las ultimas predicciones de salto(lo que construye la GBHR) - Puede considerarse la tabla  que guarda la historia de los saltos 
    unsigned char *l2table; //-> puntero PHT - Tabla que contiene los contadores para las predicciones
} two;
```

#### bpred.h
```c
// bpred.h ---------------------------------------------------------------------------------------------------------------
//------------------------------------------------------------------------------------------------------------------------

/* branch predictor types */
enum bpred_class {
  BPredComb,                    /* combined predictor (McFarling) */
  BPred2Level,			/* 2-level correlating pred w/2-bit counters */
  BPredYags,      /* YAGS predictor ------------------------------------------------------------CAMBIO*/
  BPred2bit,			/* 2-bit saturating cntr pred (dir mapped) */
  BPredTaken,			/* static predict taken */
  BPredNotTaken,		/* static predict not taken */
  BPred_NUM
};

/* direction predictor def */
struct bpred_dir_t {
  enum bpred_class class;	/* type of predictor */
  union {
    struct {
      unsigned int size;	/* number of entries in direct-mapped table */
      unsigned char *table;	/* prediction state table */
    } bimod;
    struct {
      int l1size;		/* level-1 size, number of history regs */
      int l2size;		/* level-2 size, number of pred states */
      int shift_width;		/* amount of history in level-1 shift regs */
      int xor;			/* history xor address flag */
      int *shiftregs;		/* level-1 history table */
      unsigned char *l2table;	/* level-2 prediction state table */
      int t_size;     //tamaño de la tabla de taken ------------------------------------------CAMBIO
      int nt_size;    //tamaño de la tabla de not taken ------------------------------------------CAMBIO
      unsigned char *taken_table; //tabla de taken --------------------------------------------------CAMBIO
      unsigned char *nottaken_table;  //tabla de not taken ------------------------------------------CAMBIO
    } two;
  } config;
};
```
#### bpred.c
```c
// bpred.c ---------------------------------------------------------------------------------------------------------------
//------------------------------------------------------------------------------------------------------------------------

/* create a branch predictor */
struct bpred_t *			/* branch predictory instance */
bpred_create(enum bpred_class class,	/* type of predictor to create */
	     unsigned int bimod_size,	/* bimod table size */
	     unsigned int l1size,	/* 2lev l1 table size */
	     unsigned int l2size,	/* 2lev l2 table size */
	     unsigned int meta_size,	/* meta table size */
	     unsigned int shift_width,	/* history register width */
	     unsigned int xor,  	/* history xor address flag */
	     unsigned int btb_sets,	/* number of sets in BTB */ 
	     unsigned int btb_assoc,	/* BTB associativity */
	     unsigned int retstack_size,  /* num entries in ret-addr stack */
       unsigned int t_size,   //tamaño de la tabla de taken for Yags------------------------------------------CAMBIO 
       unsigned int nt_size)  //tamaño de la tabla de not taken for Yags ------------------------------------------CAMBIO
{
  struct bpred_t *pred;

  if (!(pred = calloc(1, sizeof(struct bpred_t))))
    fatal("out of virtual memory");

  pred->class = class;

  switch (class) {
  case BPredComb:
    /* bimodal component */
    pred->dirpred.bimod = 
      bpred_dir_create(BPred2bit, bimod_size, 0, 0, 0, 0, 0); //0, 0 añadido por yags(t_size,nt_size) ----------------------------------

    /* 2-level component */
    pred->dirpred.twolev = 
      bpred_dir_create(BPred2Level, l1size, l2size, shift_width, xor, 0, 0);//0, 0 añadido por yags(t_size,nt_size) --------------------

    /* metapredictor component */
    pred->dirpred.meta = 
      bpred_dir_create(BPred2bit, meta_size, 0, 0, 0, 0, 0);//0, 0 añadido por yags(t_size,nt_size) ------------------------------------

    break;

  case BPred2Level:
    pred->dirpred.twolev = 
      bpred_dir_create(class, l1size, l2size, shift_width, xor, 0, 0); //0, 0 añadido por yags(t_size,nt_size) -------------------------

    break;
  
  case BPredYags:               //CAMBIO---------------------------------------------------------------------------------------
    pred->dirpred.yags =
      bpred_dir_create(class, l1size, l2size, shift_width, xor, nt_size, t_size);

  case BPred2bit:
    pred->dirpred.bimod = 
      bpred_dir_create(class, bimod_size, 0, 0, 0, 0, 0); //0, 0 añadido por yags(t_size,nt_size) ----------------------

  case BPredTaken:
  case BPredNotTaken:
    /* no other state */
    break;

  default:
    panic("bogus predictor class");
  }

  /* allocate ret-addr stack */
  switch (class) {
  case BPredComb:
  case BPred2Level:
  case BPredYags:               //CAMBIO---------------------------------------------------------------------
  case BPred2bit:
    {
      int i;

      /* allocate BTB */
      if (!btb_sets || (btb_sets & (btb_sets-1)) != 0)
	fatal("number of BTB sets must be non-zero and a power of two");
      if (!btb_assoc || (btb_assoc & (btb_assoc-1)) != 0)
	fatal("BTB associativity must be non-zero and a power of two");

      if (!(pred->btb.btb_data = calloc(btb_sets * btb_assoc,
					sizeof(struct bpred_btb_ent_t))))
	fatal("cannot allocate BTB");

      pred->btb.sets = btb_sets;
      pred->btb.assoc = btb_assoc;

      if (pred->btb.assoc > 1)
	for (i=0; i < (pred->btb.assoc*pred->btb.sets); i++)
	  {
	    if (i % pred->btb.assoc != pred->btb.assoc - 1)
	      pred->btb.btb_data[i].next = &pred->btb.btb_data[i+1];
	    else
	      pred->btb.btb_data[i].next = NULL;
	    
	    if (i % pred->btb.assoc != pred->btb.assoc - 1)
	      pred->btb.btb_data[i+1].prev = &pred->btb.btb_data[i];
	  }

      /* allocate retstack */
      if ((retstack_size & (retstack_size-1)) != 0)
	fatal("Return-address-stack size must be zero or a power of two");
      
      pred->retstack.size = retstack_size;
      if (retstack_size)
	if (!(pred->retstack.stack = calloc(retstack_size, 
					    sizeof(struct bpred_btb_ent_t))))
	  fatal("cannot allocate return-address-stack");
      pred->retstack.tos = retstack_size - 1;
      
      break;
    }

  case BPredTaken:
  case BPredNotTaken:
    /* no other state */
    break;

  default:
    panic("bogus predictor class");
  }

  return pred;
}

/* create a branch direction predictor */
struct bpred_dir_t *		/* branch direction predictor instance */
bpred_dir_create (
  enum bpred_class class,	/* type of predictor to create */
  unsigned int l1size,	 	/* level-1 table size */
  unsigned int l2size,	 	/* level-2 table size (if relevant) */
  unsigned int shift_width,	/* history register width */
  unsigned int xor,   	    	/* history xor address flag */
  unsigned int t_size,    //tamaño de la tabla de taken for Yags ------------------------------------------CAMBIO
  unsigned int nt_size)   //tamaño de la tabla de not taken for Yags ------------------------------------------CAMBIO
{
  struct bpred_dir_t *pred_dir;
  unsigned int cnt;
  int flipflop;

  if (!(pred_dir = calloc(1, sizeof(struct bpred_dir_t))))
    fatal("out of virtual memory");

  pred_dir->class = class;

  cnt = -1;
  switch (class) {
  case BPred2Level:
    {
      if (!l1size || (l1size & (l1size-1)) != 0)
	fatal("level-1 size, `%d', must be non-zero and a power of two", 
	      l1size);
      pred_dir->config.two.l1size = l1size;
      
      if (!l2size || (l2size & (l2size-1)) != 0)
	fatal("level-2 size, `%d', must be non-zero and a power of two", 
	      l2size);
      pred_dir->config.two.l2size = l2size;
      
      if (!shift_width || shift_width > 30)
	fatal("shift register width, `%d', must be non-zero and positive",
	      shift_width);
      pred_dir->config.two.shift_width = shift_width;
      
      pred_dir->config.two.xor = xor;
      pred_dir->config.two.shiftregs = calloc(l1size, sizeof(int));
      if (!pred_dir->config.two.shiftregs)
	fatal("cannot allocate shift register table");
      
      pred_dir->config.two.l2table = calloc(l2size, sizeof(unsigned char));
      if (!pred_dir->config.two.l2table)
	fatal("cannot allocate second level table");

      /* initialize counters to weakly this-or-that */
      flipflop = 1;
      for (cnt = 0; cnt < l2size; cnt++)
	{
	  pred_dir->config.two.l2table[cnt] = flipflop;
	  flipflop = 3 - flipflop;
	}

      break;
    }
  case BPredYags:   // CAMBIO DESDE AQUI-------------------------------------------------------------------------------------------------
    {
      if (!l1size || l1size != 1)
	fatal("level-1 size, `%d', must be 1",
	      l1size);
      pred_dir->config.two.l1size = l1size;
      
      if (!l2size || (l2size != 4 && l2size != 16 && l2size != 64 && l2size != 256 && l2size != 1024))
	fatal("level-2 size, `%d', must be non-zero and a power of two(4, 16, 64, 256, 1024)", 
	      l2size);
      pred_dir->config.two.l2size = l2size;
      
      if (!shift_width || (shift_width != 1 && shift_width != 2 && shift_width != 3 && shift_width != 4 && shift_width != 5))     //PENDIENTE DE REVISAR
	fatal("shift register width, `%d', must be non-zero and a number between 1 and 5",
	      shift_width);
      pred_dir->config.two.shift_width = shift_width;
      
      pred_dir->config.two.xor = xor;
      pred_dir->config.two.shiftregs = calloc(l1size, sizeof(int));
      if (!pred_dir->config.two.shiftregs)
	fatal("cannot allocate shift register table");
      
      pred_dir->config.two.l2table = calloc(l2size, sizeof(unsigned char));
      if (!pred_dir->config.two.l2table)
	fatal("cannot allocate second level table");

      /* initialize counters to weakly this-or-that */
      flipflop = 1;
      for (cnt = 0; cnt < l2size; cnt++)
	    {
	      pred_dir->config.two.l2table[cnt] = flipflop;
	      flipflop = 3 - flipflop;
	    }
      //Hasta aqui es como el 2level, falta inicializar las tablas de taken y not taken
      if (!t_size || (t_size != 1 && t_size != 2 && t_size != 8 && t_size != 32 && t_size != 128))
	fatal("Taken PHT size, `%d', must be non-zero and a power of two(1, 2, 8, 32, 128)", 
	      t_size);
      pred_dir->config.yags.t_size = t_size;

      if (!nt_size || (nt_size != 1 && nt_size != 2 && nt_size != 8 && nt_size != 32 && nt_size != 128))
	fatal("NotTaken PHT size, `%d', must be non-zero and a power of two(1, 2, 8, 32, 128)", 
	      nt_size);
      pred_dir->config.yags.nt_size = nt_size;

      pred_dir->config.yags.taken_table = calloc(t_size, sizeof(unsigned char));
      if (!pred_dir->config.yags.taken_table)
        fatal("cannot allocate taken table");
      
      pred_dir->config.yags.nottaken_table = calloc(nt_size, sizeof(unsigned char));
        if (!pred_dir->config.yags.nottaken_table)
        fatal("cannot allocate not taken table");

      break;
    }
  

  case BPred2bit:
    if (!l1size || (l1size & (l1size-1)) != 0)
      fatal("2bit table size, `%d', must be non-zero and a power of two", 
	    l1size);
    pred_dir->config.bimod.size = l1size;
    if (!(pred_dir->config.bimod.table =
	  calloc(l1size, sizeof(unsigned char))))
      fatal("cannot allocate 2bit storage");
    /* initialize counters to weakly this-or-that */
    flipflop = 1;
    for (cnt = 0; cnt < l1size; cnt++)
      {
	pred_dir->config.bimod.table[cnt] = flipflop;
	flipflop = 3 - flipflop;
      }

    break;

  case BPredTaken:
  case BPredNotTaken:
    /* no other state */
    break;

  default:
    panic("bogus branch direction predictor class");
  }

  return pred_dir;
}

md_addr_t				/* predicted branch target addr */
bpred_lookup(struct bpred_t *pred,	/* branch predictor instance */
	     md_addr_t baddr,		/* branch address */
	     md_addr_t btarget,		/* branch target if taken */
	     enum md_opcode op,		/* opcode of instruction */
	     int is_call,		/* non-zero if inst is fn call */
	     int is_return,		/* non-zero if inst is fn return */
	     struct bpred_update_t *dir_update_ptr, /* pred state pointer */
	     int *stack_recover_idx)	/* Non-speculative top-of-stack;
					 * used on mispredict recovery */
{
  struct bpred_btb_ent_t *pbtb = NULL;
  int index, i;

  if (!dir_update_ptr)
    panic("no bpred update record");

  /* if this is not a branch, return not-taken */
  if (!(MD_OP_FLAGS(op) & F_CTRL))
    return 0;

  pred->lookups++;

  dir_update_ptr->dir.ras = FALSE;
  dir_update_ptr->pdir1 = NULL;
  dir_update_ptr->pdir2 = NULL;
  dir_update_ptr->pmeta = NULL;
  /* Except for jumps, get a pointer to direction-prediction bits */
  switch (pred->class) {
    case BPredComb:
      if ((MD_OP_FLAGS(op) & (F_CTRL|F_UNCOND)) != (F_CTRL|F_UNCOND))
	{
	  char *bimod, *twolev, *meta;
	  bimod = bpred_dir_lookup (pred->dirpred.bimod, baddr);
	  twolev = bpred_dir_lookup (pred->dirpred.twolev, baddr);
	  meta = bpred_dir_lookup (pred->dirpred.meta, baddr);
	  dir_update_ptr->pmeta = meta;
	  dir_update_ptr->dir.meta  = (*meta >= 2);
	  dir_update_ptr->dir.bimod = (*bimod >= 2);
	  dir_update_ptr->dir.twolev  = (*twolev >= 2);
	  if (*meta >= 2)
	    {
	      dir_update_ptr->pdir1 = twolev;
	      dir_update_ptr->pdir2 = bimod;
	    }
	  else
	    {
	      dir_update_ptr->pdir1 = bimod;
	      dir_update_ptr->pdir2 = twolev;
	    }
	}
      break;
    case BPred2Level:
      if ((MD_OP_FLAGS(op) & (F_CTRL|F_UNCOND)) != (F_CTRL|F_UNCOND))
	{
	  dir_update_ptr->pdir1 =
	    bpred_dir_lookup (pred->dirpred.twolev, baddr);
	}
      break;
    case BPredYags:   //CAMBIO DESDE AQUI----------------------------------------------------------------------------------------
    {
        // Paso 1: Accede al PHT principal y obtiene la predicción inicial
        int pht_index = (pred->dirpred.two.shiftregs[0] << i) | (baddr & ((1 << i) - 1));
        pht_index &= (pred->dirpred.two.l2size - 1);

        unsigned char *pht_entry = &pred->dirpred.two.l2table[pht_index];
        int pht_prediction = (*pht_entry >> 1) & 1; // Predicción inicial

        // Paso 2: Determina si es necesario verificar TakenPHT o NotTakenPHT
        int table_index = (baddr >> 1) & (pred->dirpred.two.t_size - 1);
        int tag = baddr & 0x3F;

        unsigned char *alt_pht_entry = NULL;
        if (pht_prediction == 0) { // PHT predice NotTaken
            alt_pht_entry = &pred->dirpred.two.not_taken_pht[table_index];
            if ((alt_pht_entry[0] & 0x3F) == tag) // Hit en NotTakenPHT
                pht_prediction = (alt_pht_entry[1] >> 1) & 1;
        } else { // PHT predice Taken
            alt_pht_entry = &pred->dirpred.two.taken_pht[table_index];
            if ((alt_pht_entry[0] & 0x3F) == tag) // Hit en TakenPHT
                pht_prediction = (alt_pht_entry[1] >> 1) & 1;
        }

        // Guarda la información de actualización
        dir_update_ptr->pdir1 = pht_entry;
        dir_update_ptr->pdir2 = alt_pht_entry;

        // Retorna la dirección objetivo de acuerdo a la predicción
        if (pht_prediction)
            return pbtb ? pbtb->target : btarget; // Predicción de salto tomado
        else
            return baddr + sizeof(md_inst_t); // Predicción de salto no tomado
    }
    break;        //CAMBIO HASTA AQUI-------------------------------------------------------------------------------------------

    case BPred2bit:
      if ((MD_OP_FLAGS(op) & (F_CTRL|F_UNCOND)) != (F_CTRL|F_UNCOND))
	{
	  dir_update_ptr->pdir1 =
	    bpred_dir_lookup (pred->dirpred.bimod, baddr);
	}
      break;
    case BPredTaken:
      return btarget;
    case BPredNotTaken:
      if ((MD_OP_FLAGS(op) & (F_CTRL|F_UNCOND)) != (F_CTRL|F_UNCOND))
	{
	  return baddr + sizeof(md_inst_t);
	}
      else
	{
	  return btarget;
	}
    default:
      panic("bogus predictor class");
  }

  /*
   * We have a stateful predictor, and have gotten a pointer into the
   * direction predictor (except for jumps, for which the ptr is null)
   */

  /* record pre-pop TOS; if this branch is executed speculatively
   * and is squashed, we'll restore the TOS and hope the data
   * wasn't corrupted in the meantime. */
  if (pred->retstack.size)
    *stack_recover_idx = pred->retstack.tos;
  else
    *stack_recover_idx = 0;

  /* if this is a return, pop return-address stack */
  if (is_return && pred->retstack.size)
    {
      md_addr_t target = pred->retstack.stack[pred->retstack.tos].target;
      pred->retstack.tos = (pred->retstack.tos + pred->retstack.size - 1)
	                   % pred->retstack.size;
      pred->retstack_pops++;
      dir_update_ptr->dir.ras = TRUE; /* using RAS here */
      return target;
    }

#ifndef RAS_BUG_COMPATIBLE
  /* if function call, push return-address onto return-address stack */
  if (is_call && pred->retstack.size)
    {
      pred->retstack.tos = (pred->retstack.tos + 1)% pred->retstack.size;
      pred->retstack.stack[pred->retstack.tos].target = 
	baddr + sizeof(md_inst_t);
      pred->retstack_pushes++;
    }
#endif /* !RAS_BUG_COMPATIBLE */
  
  /* not a return. Get a pointer into the BTB */
  index = (baddr >> MD_BR_SHIFT) & (pred->btb.sets - 1);

  if (pred->btb.assoc > 1)
    {
      index *= pred->btb.assoc;

      /* Now we know the set; look for a PC match */
      for (i = index; i < (index+pred->btb.assoc) ; i++)
	if (pred->btb.btb_data[i].addr == baddr)
	  {
	    /* match */
	    pbtb = &pred->btb.btb_data[i];
	    break;
	  }
    }	
  else
    {
      pbtb = &pred->btb.btb_data[index];
      if (pbtb->addr != baddr)
	pbtb = NULL;
    }

  /*
   * We now also have a pointer into the BTB for a hit, or NULL otherwise
   */

  /* if this is a jump, ignore predicted direction; we know it's taken. */
  if ((MD_OP_FLAGS(op) & (F_CTRL|F_UNCOND)) == (F_CTRL|F_UNCOND))
    {
      return (pbtb ? pbtb->target : 1);
    }

  /* otherwise we have a conditional branch */
  if (pbtb == NULL)
    {
      /* BTB miss -- just return a predicted direction */
      return ((*(dir_update_ptr->pdir1) >= 2)
	      ? /* taken */ 1
	      : /* not taken */ 0);
    }
  else
    {
      /* BTB hit, so return target if it's a predicted-taken branch */
      return ((*(dir_update_ptr->pdir1) >= 2)
	      ? /* taken */ pbtb->target
	      : /* not taken */ 0);
    }
}

/* predicts a branch direction */
char *						/* pointer to counter */
bpred_dir_lookup(struct bpred_dir_t *pred_dir,	/* branch dir predictor inst */
		 md_addr_t baddr)		/* branch address */
{
  unsigned char *p = NULL;

  /* Except for jumps, get a pointer to direction-prediction bits */
  switch (pred_dir->class) {
    case BPred2Level:
      {
	int l1index, l2index;

        /* traverse 2-level tables */
        l1index = (baddr >> MD_BR_SHIFT) & (pred_dir->config.two.l1size - 1);
        l2index = pred_dir->config.two.shiftregs[l1index];
        if (pred_dir->config.two.xor)
	  {
#if 1
	    /* this L2 index computation is more "compatible" to McFarling's
	       verison of it, i.e., if the PC xor address component is only
	       part of the index, take the lower order address bits for the
	       other part of the index, rather than the higher order ones */
	    l2index = (((l2index ^ (baddr >> MD_BR_SHIFT))
			& ((1 << pred_dir->config.two.shift_width) - 1))
		       | ((baddr >> MD_BR_SHIFT)
			  << pred_dir->config.two.shift_width));
#else
	    l2index = l2index ^ (baddr >> MD_BR_SHIFT);
#endif
	  }
	else
	  {
	    l2index =
	      l2index
		| ((baddr >> MD_BR_SHIFT) << pred_dir->config.two.shift_width);
	  }
        l2index = l2index & (pred_dir->config.two.l2size - 1);

        /* get a pointer to prediction state information */
        p = &pred_dir->config.two.l2table[l2index];
      }
      break;
    case BPredYags:   //CAMBIO DESDE AQUI----------------------------------------------------------------------------------------
    {
        int pht_index, tag_index;
        unsigned char *pht_entry;

        // Paso 1: Calcula el índice del PHT principal
        int l1_index = (baddr >> MD_BR_SHIFT) & (pred_dir->config.two.l1size - 1);
        pht_index = pred_dir->config.two.shiftregs[l1_index]; // Obtiene la historia

        // Calcula el índice en el PHT con XOR si está habilitado
        if (pred_dir->config.two.xor) {
            pht_index = (((pht_index ^ (baddr >> MD_BR_SHIFT))
                         & ((1 << pred_dir->config.two.shift_width) - 1))
                         | ((baddr >> MD_BR_SHIFT) << pred_dir->config.two.shift_width));
        } else {
            pht_index = (pht_index | ((baddr >> MD_BR_SHIFT) << pred_dir->config.two.shift_width));
        }

        // Limita el índice al tamaño del PHT
        pht_index &= (pred_dir->config.two.l2size - 1);
        pht_entry = &pred_dir->config.two.l2table[pht_index]; // Entrada del PHT principal

        // Paso 2: Decide si buscar en TakenPHT o NotTakenPHT
        int pht_prediction = (*pht_entry >> 1) & 1; // Predicción inicial basada en el bit más significativo
        tag_index = (baddr >> 1) & (pred_dir->config.two.t_size - 1); // Índice en TakenPHT/NotTakenPHT
        int tag = baddr & 0x3F; // TAG de 6 bits para comparación

        if (pht_prediction == 0) { // Si PHT predice NotTaken
            // Verifica en NotTakenPHT
            if ((pred_dir->config.two.not_taken_pht[tag_index] & 0x3F) == tag) {
                p = &pred_dir->config.two.not_taken_pht[tag_index]; // Si hay un hit, apunta a NotTakenPHT
            } else {
                p = pht_entry; // Si no hay hit, usa la predicción del PHT
            }
        } else { // Si PHT predice Taken
            // Verifica en TakenPHT
            if ((pred_dir->config.two.taken_pht[tag_index] & 0x3F) == tag) {
                p = &pred_dir->config.two.taken_pht[tag_index]; // Si hay un hit, apunta a TakenPHT
            } else {
                p = pht_entry; // Si no hay hit, usa la predicción del PHT
            }
        }
    }
    break;      //CAMBIO HASTA AQUI-------------------------------------------------------------------------------------------

    case BPred2bit:
      p = &pred_dir->config.bimod.table[BIMOD_HASH(pred_dir, baddr)];
      break;
    case BPredTaken:
    case BPredNotTaken:
      break;
    default:
      panic("bogus branch direction predictor class");
    }

  return (char *)p;
}
```

#### sim-outorder.c