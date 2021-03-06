# -*- coding: utf-8 -*-
"""
Created on Wed Aug 12 13:37:30 2020

@author: Lab006

"""


import os
import pandas as pd
from pyteomics import fasta
import logging
from collections import Counter
import re

ACIDS_LIST = ['Y','W','F','M','L','I','V','A','C','P','G','H','R','K','T','S','Q','N','E','D','-']


def saving(args):

    sample_saving_dir = os.path.join(args.working_dir, args.name_sample)
    results_saving_dir = os.path.join(sample_saving_dir, args.modification + '_' +
                                      args.modification_site + str(args.interval_length) + '_' + args.algorithm)

    if not (os.path.exists(sample_saving_dir)):
        os.mkdir(sample_saving_dir)
        if not (os.path.exists(results_saving_dir)):
            os.mkdir(results_saving_dir)
    else:
        if not (os.path.exists(results_saving_dir)):
            os.mkdir(results_saving_dir)
#    logging.basicConfig(level = logging.DEBUG,filename=os.path.join(results_saving_dir,'mylog.log'))        
    # logging.info(u'Directories for result saving are created')       
    return  sample_saving_dir, results_saving_dir

#TODO: check this function
def fasta_match(row, bg_fasta, interval_length, modification_site):
    """Unless takes interval in the peptides, tries to find peptide in Fasta"""
    intervals = set()
    # if not intervals:
    pep_seq = row['Peptide']
    # print('pep_seq',pep_seq)
    for asterisks, modif in enumerate(re.finditer('\*', pep_seq), 1):
        # print('asterisks, modif', asterisks, modif)
        if pep_seq[modif.span()[0] - 1] == modification_site:
            # print('modif.span()',modif.span(),modif.span()[0])
            interval_start = modif.span()[0] - interval_length - asterisks
            interval_end = interval_start + 2 * interval_length + 1
            # print('start & end',interval_start,interval_end)
            if interval_start >= 0 and interval_length < len(pep_seq.replace('*', '')):
                intervals.update([pep_seq.replace('*', '')[interval_start: interval_end]])
            else:
                # logging.info('Can not take interval %s.', row['Peptide'])
                logging.info('Can not take interval %s. Try to find peptide in fasta file.', row['Peptide'])
                fasta_intervals = []
                for name, seq in bg_fasta.items():
                    i = 0
                    start = seq[i:].find(row['Peptide'].replace('*', ''))
                    i = start
                    while start >= 0:
                        for asterisks, modif in enumerate(re.finditer('\*', row['Peptide']), 1):
                            interval_start = i + modif.span()[0] - interval_length - asterisks
                            interval_end = interval_start + 2 * interval_length + 1
                            interval = seq[interval_start: interval_end]
                            fasta_intervals.append(interval)
                        start = seq[i + 1:].find(row['Peptide'].replace('*', ''))
                        i += start + 1
                if len(fasta_intervals) > 0:
                    logging.info('%s found in fasta.', row['Peptide'])
                    intervals.update(fasta_intervals)
        else:
            logging.info('Peptide has another modification site %s', row['Peptide'])
                # print('final_int',pep_seq.replace('*', '')[interval_start: interval_end])
    return list(intervals)


def background_maker(args):
#    print('Making background DB')
    #хотим сделать background из идентифицированных белков
    bg_fasta = dict()
    # bg = defaultdict()
    background = set()
    with fasta.read(args.fasta) as f:
        for name, sequence in f:
            name_id = name.split('|')[1]
            extended_seq = ''.join(['-' * args.interval_length, sequence, '-' * args.interval_length])
            bg_fasta[name_id] = extended_seq
            mod_aa_indexes = re.finditer(args.modification_site, extended_seq)
            bg_intervals = [extended_seq[i.span()[0] - args.interval_length: i.span()[0] + args.interval_length + 1] for i in mod_aa_indexes]
            # bg[name_id] = bg_intervals
            background.update(bg_intervals)

    logging.info(u'Set of %s background intervals is created', len(background))
    logging.debug(u'Background DB is ready')    
    with open('bg.csv', 'w') as f:
        f.write('\n'.join(background))
    return pd.DataFrame([list(i) for i in background], columns=range(-args.interval_length, args.interval_length + 1)), bg_fasta   


#функции для валидации


def get_occurences(intervals_df, acids=ACIDS_LIST):
    logging.debug('Intervals list length:\n%s', len(intervals_df))
    occ = pd.DataFrame(index=acids)
    occ[intervals_df.columns] = intervals_df.apply(lambda x: pd.Series(Counter(x)), axis=0)
    return occ


# def saving_table(results_saving_dir, result, interval_length, name):
#     path=os.path.join(results_saving_dir, 'table' + str(interval_length) + '_' + name + '.csv')
#     result.to_csv(path)   
 
    
def peptides_table(args, sample_saving_dir, bg_fasta):
    Peptides = pd.read_table(args.dataset, names=['Peptide'])
    logging.info('Peptide table contains %d peptides', Peptides.shape[0])
    logging.debug('Initial Peptides df:\n%s', Peptides.head())
    Peptides['fasta_match'] = Peptides.apply(fasta_match, args=[bg_fasta, args.interval_length, args.modification_site], axis=1)
    logging.info('Found %d peptides motifs', len(set(Peptides['fasta_match'].sum())))
    Peptides.to_csv(os.path.join(sample_saving_dir, 'peptide_identification.csv'), mode='w')
    logging.debug('Prepared Peptides df:\n%s', Peptides)
    return Peptides    

