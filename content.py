import xml.dom.minidom as minidom
import xml.dom
import logging
import os, os.path
import utils

class OPSContent(object):
    '''A class for instantiating content xml documents in the OPS Preferred
    Vocabulary'''
    def __init__(self, documentstring, doi, outdirect, document):
        print('Generating OPS content...')
        self.inputstring = documentstring
        self.doc = minidom.parse(self.inputstring)
        #Get string from outdirect sans "journal."
        self.doi = doi
        self.jid = self.doi.split('journal.')[1] #journal id string
        self.syn_frag = 'synop.{0}.xml'.format(self.jid) + '#{0}'
        self.main_frag = 'main.{0}.xml'.format(self.jid) + '#{0}'
        self.bib_frag = 'biblio.{0}.xml'.format(self.jid) + '#{0}'
        self.tab_frag = 'tables.{0}.xml'.format(self.jid) + '#{0}'
        self.outdir = os.path.join(outdirect, 'OPS')
        self.outputs = {'Synopsis': os.path.join(outdirect, 'OPS', 'synop.{0}.xml'.format(self.jid)), 
                        'Main': os.path.join(outdirect, 'OPS', 'main.{0}.xml'.format(self.jid)), 
                        'Biblio': os.path.join(outdirect, 'OPS', 'biblio.{0}.xml'.format(self.jid)), 
                        'Tables': os.path.join(outdirect, 'OPS', 'tables.{0}.xml'.format(self.jid))}
        self.metadata = document.front
        self.backdata = document.back
        
        self.createSynopsis(self.metadata, self.backdata)
        self.createMain()
        try:
            back = self.doc.getElementsByTagName('back')[0]
        except IndexError:
            pass
        else:
            self.createBiblio(self.doc, back)
        
    def createSynopsis(self, meta, back):
        '''Create an output file containing a representation of the article 
        synopsis'''
        
        #Initiate the document, returns the document and its body element
        synop, synbody = self.initiateDocument('Synopsis file')
        
        #Create the title for the article
        title = synbody.appendChild(synop.createElement('h1'))
        title.setAttribute('id', 'title')
        title.setAttribute('class', 'article-title')
        title.childNodes = meta.article_meta.article_title.childNodes
        
        #Affiliation index to be generated as authors parsed
        affiliation_index = []
        
        #Create authors
        self.synopsisAuthors(meta, synbody, synop)
        
        #Create a node for the affiliation text
        aff_node = synop.createElement('p')
        art_affs = meta.article_meta.art_affs
        if art_affs:
            for item in art_affs:
                if 'aff' in item.rid:
                    sup = synop.createElement('sup')
                    sup.setAttribute('id', item.rid)
                    sup.appendChild(synop.createTextNode(str(art_affs.index(item) + 1)))
                    aff_node.appendChild(sup)
                    aff_node.appendChild(synop.createTextNode(item.address))
            synbody.appendChild(aff_node)
        
        #Create the Abstract if it exists
        try:
            abstract = meta.article_meta.abstracts['default']
        except KeyError:
            pass
        else:
            abstitle = synbody.appendChild(synop.createElement('h2'))
            abstitle.appendChild(synop.createTextNode('Abstract'))
            synbody.appendChild(abstract)
            abstract.tagName = 'div'
            abstract.setAttribute('id', 'abstract')
            abstract.setAttribute('class', 'abstract')
            for title in abstract.getElementsByTagName('title'):
                title.tagName = 'h3'
            for sec in abstract.getElementsByTagName('sec'):
                sec.tagName = 'div'
            self.postNodeHandling(abstract, synop)
        
        #Create the Author's Summary if it exists
        try:
            summary = meta.article_meta.abstracts['summary']
        except KeyError:
            pass
        else:
            summary_title = synbody.appendChild(synop.createElement('h2'))
            summary_title.appendChild(synop.createTextNode('Author Summary'))
            for title in summary.getElementsByTagName('title'):
                if utils.serializeText(title, stringlist = []) == 'Author Summary':
                    summary.removeChild(title)
            synbody.appendChild(summary)
            summary.tagName = 'div'
            summary.removeAttribute('abstract-type')
            summary.setAttribute('id', 'author-summary')
            summary.setAttribute('class', 'summary')
            for title in abstract.getElementsByTagName('title'):
                title.tagName = 'h3'
            for sec in abstract.getElementsByTagName('sec'):
                sec.tagName = 'div'
            #for para in abstract.getElementsByTagName('p'):
            #    para.tagName = 'big'
            self.postNodeHandling(abstract, synop)
        
        #We can create the <div class="articleInfo">
        #We will put metadata in it.
        articleInfo = synbody.appendChild(synop.createElement('div'))
        articleInfo.setAttribute('class', 'articleInfo')
        articleInfo.setAttribute('id', 'articleInfo')
        
        #Citation text should be first, but I am unsure of PLoS's rules for it
        #For now I will just place the DOI
        citation = articleInfo.appendChild(synop.createElement('p'))
        label = citation.appendChild(synop.createElement('b'))
        label.appendChild(synop.createTextNode('Citation: '))
        citation.appendChild(synop.createTextNode('doi:{0}'.format(self.doi)))
        
        #Handle Editors
        for editor in meta.article_meta.art_edits:
            name = editor.get_name()
            role = editor.role
            affs = editor.affiliation
            ped = articleInfo.appendChild(synop.createElement('p'))
            label = ped.appendChild(synop.createElement('b'))
            if role:
                label.appendChild(synop.createTextNode('{0}: '.format(role)))
            else:
                label.appendChild(synop.createTextNode('Editor: '))
            ped.appendChild(synop.createTextNode(u'{0}, '.format(name)))
            first_aff = True
            for aff in affs:
                for item in meta.article_meta.art_affs:
                    if item.rid == aff:
                        address = item.address
                        if first_aff:
                            ped.appendChild(synop.createTextNode(u'{0}'.format(address)))
                            first_aff = False
                        else:
                            ped.appendChild(synop.createTextNode(u'; {0}'.format(address)))
        
        #Create a node for the dates
        datep = articleInfo.appendChild(synop.createElement('p'))
        datep.setAttribute('id', 'dates')
        hist = meta.article_meta.history
        dates = meta.article_meta.art_dates
        if hist:
            datelist = [('Received', hist['received']), 
                        ('Accepted', hist['accepted']), 
                        ('Published', dates['epub'])]
        else:
            datelist = [('Published', dates['epub'])]
        
        for _bold, _data in datelist:
            bold = datep.appendChild(synop.createElement('b'))
            bold.appendChild(synop.createTextNode('{0} '.format(_bold)))
            datestring = _data.niceString()
            datep.appendChild(synop.createTextNode('{0} '.format(datestring)))
        
        #Create a node for the Copyright text:
        copp = articleInfo.appendChild(synop.createElement('p'))
        copp.setAttribute('id', 'copyright')
        copybold = copp.appendChild(synop.createElement('b'))
        copybold.appendChild(synop.createTextNode('Copyright: '))
        copystr = u'{0} {1}'.format(u'\u00A9', 
                                    meta.article_meta.art_copyright_year)
        copp.appendChild(synop.createTextNode(copystr))
        copp.childNodes += meta.article_meta.art_copyright_statement.childNodes
        
        #Create a node for the Funding text
        if back and back.funding:
            fundp = articleInfo.appendChild(synop.createElement('p'))
            fundp.setAttribute('id', 'funding')
            fundbold = fundp.appendChild(synop.createElement('b'))
            fundbold.appendChild(synop.createTextNode('Funding: '))
            fundp.appendChild(synop.createTextNode(back.funding))
        
        #Create a node for the Competing Interests text
        if back and back.competing_interests:
            compip = articleInfo.appendChild(synop.createElement('p'))
            compip.setAttribute('id', 'competing-interests')
            compibold = compip.appendChild(synop.createElement('b'))
            compibold.appendChild(synop.createTextNode('Competing Interests: '))
            compip.appendChild(synop.createTextNode(back.competing_interests))
        
        #Create a node for the Abbreviations if it exists, we will interpret
        #the data in Back.glossary to generate this text
        if back and back.glossary:
            try:
                title = back.glossary.getElementsByTagName('title')[0]
            except IndexError:
                pass
            else:
                if title.firstChild.data == 'Abbreviations':
                    ap = articleInfo.appendChild(synop.createElement('p'))
                    ap.setAttribute('id', 'abbreviations')
                    apb = ap.appendChild(synop.createElement('b'))
                    apb.appendChild(synop.createTextNode('Abbreviations: '))
                    first = True
                    for item in back.glossary.getElementsByTagName('def-item'):
                        if first:
                            first = False
                        else:
                            ap.appendChild(synop.createTextNode('; '))
                        term = item.getElementsByTagName('term')[0]
                        idef = item.getElementsByTagName('def')[0]
                        defp = idef.getElementsByTagName('p')[0]
                        for c in term.childNodes:
                            ap.appendChild(c.cloneNode(deep=True))
                        ap.appendChild(synop.createTextNode(','))
                        for c in defp.childNodes:
                            ap.appendChild(c.cloneNode(deep=True))
        
        #Create a node for the correspondence text
        corr_line = articleInfo.appendChild(synop.createElement('p'))
        art_corresps = meta.article_meta.art_corresps
        correspondence_nodes = meta.article_meta.correspondences
        try:
            corr_line.setAttribute('id', art_corresps[0].rid)
        except IndexError:
            pass
        else:
            for correspondence in correspondence_nodes:
                corr_line.childNodes += correspondence.childNodes
            #corr_line.appendChild(synop.createTextNode(corresp_text))
        
        #Handle conversion of ext-link to <a>
        ext_links = synop.getElementsByTagName('ext-link')
        for ext_link in ext_links:
            ext_link.tagName = u'a'
            ext_link.removeAttribute('ext-link-type')
            href = ext_link.getAttribute('xlink:href')
            ext_link.removeAttribute('xlink:href')
            ext_link.removeAttribute('xlink:type')
            ext_link.setAttribute('href', href)
        
        #Generate an articleInfo segment for the author notes current affs
        anca = meta.article_meta.author_notes_current_affs
        for id in sorted(anca.iterkeys()):
            label, data = anca[id]
            cap = articleInfo.appendChild(data)
            cap.setAttribute('id', id)
            cab = cap.insertBefore(synop.createElement('b'), cap.firstChild)
            cab.appendChild(synop.createTextNode(label))
        
        #If there are other footnotes in Author notes, eg. <fn fn-typ="other"
        #Place them here.
        ano = meta.article_meta.author_notes_other
        for id in sorted(ano.iterkeys()):
            cap = articleInfo.appendChild(ano[id])
            cap.setAttribute('id', id)
        
        #Create the Editor's abstract if it exists
        try:
            editor_abs = meta.article_meta.abstracts['editor']
        except KeyError:
            pass
        else:
            for child in editor_abs.childNodes:
                try:
                    if child.tagName == u'title':
                        title = child
                        break
                except AttributeError:
                    pass
            synbody.appendChild(title)
            title.tagName = u'h2'
            synbody.appendChild(editor_abs)
            editor_abs.tagName = 'div'
            editor_abs.removeAttribute('abstract-type')
            editor_abs.setAttribute('id','editor_abstract')
            editor_abs.setAttribute('class', 'editorsAbstract')
            for title in editor_abs.getElementsByTagName('title'):
                title.tagName = 'h3'
            for sec in editor_abs.getElementsByTagName('sec'):
                sec.tagName = 'div'
            #for para in editor_abs.getElementsByTagName('p'):
            #    para.tagName = 'big'
            self.postNodeHandling(editor_abs, synop)
        
        
        self.postNodeHandling(synbody, synop)
        
        with open(self.outputs['Synopsis'],'wb') as out:
            out.write(synop.toprettyxml(encoding = 'utf-8'))

    def createMain(self):
        '''Create an output file containing the main article body content'''
        doc = self.doc
        #Initiate the document, returns the document and its body element
        main, mainbody = self.initiateDocument('Main file')
        body = doc.getElementsByTagName('body')[0]
        #Here we copy the entirety of the body element over to our main document
        for item in body.childNodes:
            mainbody.appendChild(item.cloneNode(deep=True))
        #Process figures
        self.figNodeHandler(mainbody, main) #Convert <fig> to <img>
        #Process tables
        tab_doc, tab_docbody = self.initiateDocument('HTML Versions of Tables')
        self.tableWrapNodeHandler(mainbody, main, tab_docbody) #Convert <table-wrap>
        self.postNodeHandling(tab_docbody, tab_doc)
        #Process ref-list nodes
        self.refListHandler(mainbody, main)
        #Process boxed-text
        self.boxedTextNodeHandler(mainbody)
        #Process supplementary-materials
        self.supplementaryMaterialNodeHandler(mainbody, main)
        #Process Acknowledgments
        self.acknowledgments(mainbody, main)
        #Process Author Contributions
        self.authorContributions(mainbody, main)
        #General processing
        self.postNodeHandling(mainbody, main, ignorelist=[])
        #Conversion of existing <div><title/></div> to <div><h#/></div>
        self.divTitleFormat(mainbody, depth = 0) #Convert <title> to <h#>...
        #If any tables were in the article, make the tables.xml
        if tab_docbody.getElementsByTagName('table'):
            with open(self.outputs['Tables'],'wb') as output:
                output.write(tab_doc.toprettyxml(encoding = 'utf-8'))
        
        #Write the document
        with open(self.outputs['Main'],'wb') as out:
            out.write(main.toprettyxml(encoding = 'utf-8'))
        
    def createBiblio(self, doc, back):
        '''Create an output file containing the article bibliography'''
        #Initiate the document, returns the document and its body element
        biblio, bibbody = self.initiateDocument('Bibliography file')
        
        back = doc.getElementsByTagName('back')[0]
        try:
            bibbody.appendChild(back.getElementsByTagName('ref-list')[0])
        except IndexError:
            pass
        else:
            self.refListHandler(bibbody, biblio)
            bibbody.getElementsByTagName('div')[0].setAttribute('id', 'references')
            self.postNodeHandling(bibbody, biblio, ignorelist=[])
            with open(self.outputs['Biblio'],'wb') as out:
                out.write(biblio.toprettyxml(encoding = 'utf-8'))

    def synopsisAuthors(self, meta, topnode, doc):
        '''Creates the text in synopsis for displaying the authors'''
        authors = meta.article_meta.art_auths
        auth_node = topnode.appendChild(doc.createElement('h3'))
        first = True
        for author in authors:
            if not first:
                auth_node.appendChild(doc.createTextNode(', '))
            else:
                first = False
            name = author.get_name()
            auth_node.appendChild(doc.createTextNode(name))
            for xref in author.xrefs:
                rid = xref.getAttribute('rid')
                try:
                    s = utils.getTagText(xref.getElementsByTagName('sup')[0])
                except IndexError:
                    s = u'!'
                if not s:
                    s = u''
                sup = auth_node.appendChild(doc.createElement('sup'))
                a = sup.appendChild(doc.createElement('a'))
                a.setAttribute('href', self.syn_frag.format(rid))
                a.appendChild(doc.createTextNode(s))
            
            
            

    def acknowledgments(self, topnode, doc):
        '''Takes the optional acknowledgments element from the back data
        and adds it to the document, it belongs right after Supporting
        Information and before Author Contributions'''
        try:
            ack = self.backdata.ack
        except AttributeError:
            #An article that has no <back> element
            pass
        else:
            if ack:
                topnode.appendChild(ack)
                ack.tagName = 'div'
                ack.setAttribute('id', 'acknowledgments')
                ack_title = doc.createElement('h2')
                ack_title.appendChild(doc.createTextNode('Acknowledgments'))
                ack.insertBefore(ack_title, ack.firstChild)

    def authorContributions(self, topnode, doc):
        '''Takes the optional Author Contributions element from metadata and
           adds it to the document, it belongs between Acknowledgments and
           References.'''
        anc = self.metadata.article_meta.author_notes_contributions
        if anc:
            topnode.appendChild(anc)
            anc.tagName = 'div'
            anc.removeAttribute('fn-type')
            anc.setAttribute('id', 'contributions')
            anc_title = doc.createElement('h2')
            anc_title.appendChild(doc.createTextNode('Author Contibutions'))
            anc.insertBefore(anc_title, anc.firstChild)
            
    def parseRef(self, fromnode, doc):
        '''Interprets the references in the article back reference list into
        comprehensible xml'''
        #Create a paragraph tag to contain the reference text data
        ref_par = doc.createElement('p')
        #Set the fragment identifier for the paragraph tag
        ref_par.setAttribute('id', fromnode.getAttribute('id'))
        #Pull the label node into a node_list
        label = fromnode.getElementsByTagName('label')[0]
        try:
            #Collect the citation tag and its citation type
            citation = fromnode.getElementsByTagName('citation')[0]
        except IndexError:
            #The article may have used <nlm-citation>
            citation = fromnode.getElementsByTagName('nlm-citation')[0]
        citation_type = citation.getAttribute('citation-type')
        #A list of known citation types used by PLoS
        citation_types = ['book', 'confproc', 'gov', 'journal', 'other', 'web',
                          '']
        if citation_type not in citation_types:
            print('Unkown citation-type value: {0}'.format(citation_type))
        #Collect possible tag texts, then decide later how to format
        #article-title is treated specially because of its potential complexity
        tags = ['source', 'year', 'publisher-loc', 'publisher-name', 'comment',
                'page-count', 'fpage', 'lpage', 'month', 'volume',
                'day', 'issue', 'edition', 'page-range', 'conf-name',
                'conf-date', 'conf-loc', 'supplement']
        try:
            art_tit = citation.getElementsByTagName('article-title')[0]
        except IndexError:
            art_tit = None
        cite_tags = {}
        for each in tags:
            try:
                t = citation.getElementsByTagName(each)[0]
            except IndexError:
                t = None
            if t:
                cite_tags[each] = utils.getTagText(t)
            else:
                cite_tags[each] = ''
        
        if citation_type == u'journal':
            #The base strings with some punctuation; to be formatted with data
            frs = u'{0}. {1} {2} '  # first reference string
            srs = u' {0} {1}{2}{3} {4}'  # second reference string
            #A journal citation looks roughly like this
            #Label. Authors (Year) Article Title. Source Volume: Supplement?
            #Pages. Comment FIND ONLINE
            lbl = utils.getTagText(label)  # lbl
            auth = u''  # auth
            first = True
            first_auth = None
            for name in citation.getElementsByTagName('name'):
                surname = name.getElementsByTagName('surname')[0]
                try:
                    given = name.getElementsByTagName('given-names')[0]
                except IndexError:
                    given = ''
                if first:
                    first_auth = utils.getTagText(surname)
                    first = False
                else:
                    auth += ', '
                auth += utils.getTagText(surname)
                if given:
                    auth += u' {0}'.format(utils.getTagText(given))
            #If there is an <etal> tag, add it to the auth string
            if citation.getElementsByTagName('etal'):
                auth += ', et al.'
            year = cite_tags['year']  # year
            if year:
                year = '({0})'.format(year)
            #Format the first reference string with our data
            frs = frs.format(lbl, auth, year)
            #Append the first reference string to reference paragraph
            ref_par.appendChild(doc.createTextNode(frs))
            #Give all the article title children to reference paragraph
            if art_tit:
                ref_par.childNodes += art_tit.childNodes
            #Begin collecting data for second reference string
            src = cite_tags['source']  # src
            if src:
                src += ' '
            vol = cite_tags['volume']  # vol
            if cite_tags['issue']:  # If issue has a value, we add it to vol
                vol += u'({0})'.format(cite_tags['issue'])
            if vol:
                vol += ': '
            if cite_tags['supplement']:
                supp = cite_tags['supplement'] + ' '  # supp
            else:
                supp = ''  # supp
            fpage, lpage = cite_tags['fpage'],cite_tags['lpage']
            if fpage and lpage:
                pgs = u'{0}-{1}'.format(fpage, lpage)  # pgs
            else:
                pgs = fpage + lpage  # pgs
            if pgs:
                pgs += '.'
            com = cite_tags['comment']  # com
            srs = srs.format(src, vol, supp, pgs, com)
            ref_par.appendChild(doc.createTextNode(srs))
            if com == 'doi:':  # PLoS put in a direct dx.doi link
                ext_link = citation.getElementsByTagName('ext-link')[0]
                ext_link_text = utils.getTagText(ext_link)
                href = ext_link.getAttribute('xlink:href')
                alink = doc.createElement('a')
                alink.appendChild(doc.createTextNode(ext_link_text))
                alink.setAttribute('href', href)
                ref_par.appendChild(alink)
            else:
                alink = doc.createElement('a')
                alink.appendChild(doc.createTextNode('Find This Article Online'))
                j_title = self.metadata.journal_meta.title[0]
                pj= {'PLoS Genetics': u'http://www.plosgenetics.org/{0}{1}{2}{3}',
                     'PLoS ONE': u'http://www.plosone.org/{0}{1}{2}{3}',
                     'PLoS Biology': u'http://www.plosbiology.org/{0}{1}{2}{3}',
                     'PLoS Computational Biology': u'http://www.ploscompbiol.org/{0}{1}{2}{3}',
                     'PLoS Pathogens': u'http://www.plospathogens.org/{0}{1}{2}{3}',
                     'PLoS Medicine': u'http://www.plosmedicine.org/{0}{1}{2}{3}',
                     'PLoS Neglected Tropical Diseases':
                     u'http://www.plosntds.org/{0}{1}{2}{3}'}
                if art_tit:
                    art_tit_form = utils.serializeText(art_tit, stringlist=[]).replace(' ', '%20')
                    href = pj[j_title].format(u'article/findArticle.action?author=',
                                              first_auth, u'&title=', art_tit_form)
                    alink.setAttribute('href', href)
                    ref_par.appendChild(alink)
        elif citation_type == u'confproc':
            #The base strings with some punctuation; to be formatted with data
            frs = u'{0}. {1} '  # first reference string
            srs = u' {0} {1}{2}{3}'  # second reference string
            #A confproc citation looks roughly like this
            #Label. Editors Article Title. Conference Name; Conference Date;
            #Conference Location. (Year) Comment.
            lbl = utils.getTagText(label)  # lbl
            auth = u''  # auth
            first = True
            for name in citation.getElementsByTagName('name'):
                surname = name.getElementsByTagName('surname')[0]
                try:
                    given = name.getElementsByTagName('given-names')[0]
                except IndexError:
                    given = ''
                if first:
                    first = False
                else:
                    auth += ', '
                auth += utils.getTagText(surname)
                if given:
                    auth += u' {0}'.format(utils.getTagText(given))
            #If there is an <etal> tag, add it to the auth string
            if citation.getElementsByTagName('etal'):
                auth += ', et al.'
            #Format the first reference string with our data
            frs = frs.format(lbl, auth)
            #Append the first reference string to reference paragraph
            ref_par.appendChild(doc.createTextNode(frs))
            #Give all the article title children to reference paragraph
            if art_tit:
                ref_par.childNodes += art_tit.childNodes
            cname = cite_tags['conf-name']  # cname
            if cname:
                cname += '; '
            cdate = cite_tags['conf-date']  # cdate
            if cdate:
                cdate += '; '
            cloc = cite_tags['conf-loc']  # cloc
            if cloc:
                cloc += '; '
            year = cite_tags['year']  # year
            if year:
                year = '({0}) '.format(year)
            srs = srs.format(cname, cdate, cloc, year)
            ref_par.appendChild(doc.createTextNode(srs))
            try:
                com = citation.getElementsByTagName('comment')[0]
            except IndexError:
                ref_par.appendChild(doc.createTextNode('.'))
            else:
                for ext_link in com.getElementsByTagName('ext-link'):
                    ext_link.removeAttribute('ext-link-type')
                    ext_link.removeAttribute('xlink:type')
                    href = ext_link.getAttribute('xlink:href')
                    ext_link.removeAttribute('xlink:href')
                    ext_link.tagName = 'a'
                    ext_link.setAttribute('href', href)
                ref_par.childNodes += com.childNodes
        
        elif citation_type == u'other':
            ref_string = u'{0}. '.format(utils.getTagText(label))
            ref_string += self.refOther(citation, stringlist = [])
            ref_par.appendChild(doc.createTextNode(ref_string[:-2]))
            
        return ref_par
            
    def refOther(self, node, stringlist = []):
        '''Attempts to broadly handle Other citation types and produce a
        human-intelligible string output'''
        
        for item in node.childNodes:
            if item.nodeType == item.TEXT_NODE and not item.data == u'\n':
                if item.data.lstrip():
                    if item.parentNode.tagName == u'year':
                        stringlist.append(u'({0})'.format(item.data))
                        stringlist.append(u', ')
                    elif item.parentNode.tagName == u'source':
                        stringlist.append(u'[{0}]'.format(item.data))
                        stringlist.append(u', ')
                    elif item.parentNode.tagName == u'article-title':
                        stringlist.append(u'\"{0}\"'.format(item.data))
                        stringlist.append(u', ')
                    else:
                        stringlist.append(item.data)
                        stringlist.append(u', ')
            else:
                self.refOther(item, stringlist)
        return u''.join(stringlist)
    
    def postNodeHandling(self, topnode, doc, ignorelist = []):
        '''A wrapper function for all of the node handlers. Conceptually,
        this function should be called after special cases have been handled 
        such as in figures, tables, and references. This function provides 
        simple access to the entire cohort of default nodeHandlers which may 
        be utilized after special cases have been handled. Passing a list of 
        string tagNames allows those tags to be ignored'''
        handlers = {'bold': self.boldNodeHandler(topnode),
                    'italic': self.italicNodeHandler(topnode),
                    'monospace': self.monospaceNodeHandler(topnode),
                    'sub': self.subNodeHandler(topnode),
                    'sup': self.supNodeHandler(topnode),
                    'underline': self.underlineNodeHandler(topnode),
                    'xref': self.xrefNodeHandler(topnode),
                    'sec': self.secNodeHandler(topnode),
                    #'ref-list': self.refListHandler(topnode, doc),
                    'named-content': self.namedContentNodeHandler(topnode),
                    'inline-formula': self.inlineFormulaNodeHandler(topnode, doc),
                    'disp-formula': self.dispFormulaNodeHandler(topnode, doc),
                    'disp-quote': self.dispQuoteNodeHandler(topnode, doc),
                    'ext-link': self.extLinkNodeHandler(topnode),
                    'sc': self.smallCapsNodeHandler(topnode),
                    'list': self.listNodeHandler(topnode, doc),
                    'graphic': self.graphicNodeHandler(topnode),
                    'email': self.emailNodeHandler(topnode),
                    'fn': self.fnNodeHandler(topnode)}
        
        for tagname in handlers:
            if tagname not in ignorelist:
                handlers[tagname]
    
    def refListHandler(self, topnode, doc):
        '''This method has two primary significant uses: it is used to generate
        the bibliographical references section at the end of an article, and at
        times when a Suggested Reading list is offered in the text. In the
        latter case, it is typical to see fewer metadata items and the presence
        of a <comment> tag to illustrate why it is recommended.
        
        Because the tags used to represent metadata by and large cannot be
        interpreted in ePub, current practice involves removing the original
        ref-list node and replacing it with a rendered string andlinks to
        locate the resource online.'''
        try:
            ref_lists = topnode.getElementsByTagName('ref-list')
        except AttributeError:
            for item in topnode:
                self.figNodeHandler(item, doc)
        else:
            for rl in ref_lists:
                #We can mutate the title node to <h2>
                try:
                    title = rl.getElementsByTagName('title')[0]
                except IndexError:
                    pass
                else:
                    title.tagName = 'h2'
                #Then we want to handle each ref in the ref-list
                ref_ps = []
                for ref in rl.getElementsByTagName('ref'):
                    ref_ps.append(self.parseRef(ref, doc))
                    rl.removeChild(ref)
                #Now that we have our title text and a list of rendered
                #paragraph tags from our ref tags, we mutate the original tag
                rl.tagName = 'div'
                rl.setAttribute('class', 'ref-list')
                #Add all the ref paragraphs as children
                for each in ref_ps:
                    rl.appendChild(each)
                
    def figNodeHandler(self, topnode, doc):
        '''Handles conversion of <fig> tags under the provided topnode. Also 
        handles Nodelists by calling itself on each Node in the NodeList.'''
        try:
            fig_nodes = topnode.getElementsByTagName('fig')
        except AttributeError:
            for item in topnode:
                self.figNodeHandler(item, doc)
        else:
            for fig_node in fig_nodes:
                #These are in order
                fig_object_id = fig_node.getElementsByTagName('object-id') #zero or more
                fig_label = fig_node.getElementsByTagName('label') #zero or one
                fig_caption = fig_node.getElementsByTagName('caption') #zero or one
                #Accessibility Elements ; Any combination of
                fig_alt_text = fig_node.getElementsByTagName('alt-text')
                fig_long_desc = fig_node.getElementsByTagName('long-desc')
                #Address Linking Elements ; Any combination of
                fig_email = fig_node.getElementsByTagName('email')
                fig_ext_link = fig_node.getElementsByTagName('ext-link')
                fig_uri = fig_node.getElementsByTagName('uri')
                #Document location information
                fig_parent = fig_node.parentNode
                orig_parent = fig_node.parentNode
                fig_sibling = fig_node.nextSibling
                
                #There is a bizarre circumstance where some figures are placed
                #In an invalid position for ePub xml
                #Here is a fix for it
                if fig_parent.tagName == 'body':
                    fig_div = doc.createElement('div')
                    fig_parent.insertBefore(fig_div, fig_node)
                    fig_div.appendChild(fig_node)
                    fig_parent = fig_div  # this equates to fig_node.parentNode
                
                #This should provide the fragment identifier
                fig_id = fig_node.getAttribute('id')
                
                if fig_alt_text: #Extract the alt-text if list non-empty
                    fig_alt_text_text = utils.getTagData(fig_alt_text)
                else:
                    fig_alt_text_text = 'A figure'
                    
                if fig_long_desc:
                    fig_long_desc_text = utils.getTagData(fig_long_desc)
                else:
                    fig_long_desc_text = None
                
                #In this case, we will create an <img> node to replace <fig>
                img_node = doc.createElement('img')
                
                #The following code block uses the fragment identifier to
                #locate the correct source file based on PLoS convention
                name = fig_id.split('-')[-1]
                startpath = os.getcwd()
                os.chdir(self.outdir)
                for path, _subdirs, filenames in os.walk('images-{0}'.format(self.jid)):
                    for filename in filenames:
                        if os.path.splitext(filename)[0] == name:
                            img_src = os.path.join(path, filename)
                os.chdir(startpath)
                #Now we can begin to process to output
                try:
                    img_node.setAttribute('src', img_src)
                except NameError:
                    logging.error('Image source not found')
                    img_node.setAttribute('src', 'not_found')
                img_node.setAttribute('id', fig_id)
                img_node.setAttribute('alt', fig_alt_text_text)
                #The handling of longdesc is important to accessibility
                #Due to the current workflow, we will be storing the text of 
                #longdesc in the optional title attribute of <img>
                #A more optimal strategy would be to place it in its own text
                #file, we need to change the generation of the OPF to do this
                #See http://idpf.org/epub/20/spec/OPS_2.0.1_draft.htm#Section2.3.4
                if fig_long_desc_text:
                    img_node.setAttribute('title', fig_long_desc_text)
                
                #Replace the fig_node with img_node
                fig_parent.replaceChild(img_node, fig_node)
                
                #Handle the figure caption if it exists
                if fig_caption:
                    fig_caption_node = fig_caption[0] #Should only be one if nonzero
                    #We want to handle the <title> in our caption/div as a special case
                    #For this reason, figNodeHandler should be called before divTitleFormat
                    for _title in fig_caption_node.getElementsByTagName('title'):
                        _title.tagName = u'b'
                    #Modify this <caption> in situ to <div class="caption">
                    fig_caption_node.tagName = u'div'
                    fig_caption_node.setAttribute('class', 'caption')
                    if fig_label: #Extract the label text if list non-empty
                        fig_label_text = utils.getTagData(fig_label)
                        #Format the text to bold and prepend to caption children
                        bold_label_text = doc.createElement('b')
                        bold_label_text.appendChild(doc.createTextNode(fig_label_text + '.'))
                        fig_caption_node.insertBefore(bold_label_text, fig_caption_node.firstChild)
                    #Place after the image node
                    orig_parent.insertBefore(fig_caption_node, fig_sibling)
                
                #Handle email
                for email in fig_email:
                    email.tagName = 'a'
                    text = each.getTagData
                    email.setAttribute('href','mailto:{0}'.format(text))
                    if fig_sibling:
                        fig_parent.insertBefore(email, fig_sibling)
                    else:
                        fig_parent.appendChild(email)
                #ext-links are currently ignored
                
                #uris are currently ignored
                
                #Fig may contain many more elements which are currently ignored
                #See http://dtd.nlm.nih.gov/publishing/tag-library/2.0/n-un80.html
                #For more details on what could be potentially handled
                
    
    def inlineFormulaNodeHandler(self, topnode, doc):
        '''Handles <inline-formula> nodes for ePub formatting. At the moment, 
        there is no way to support MathML (without manual curation) which 
        would be more optimal for accessibility. If PLoS eventually publishes 
        the MathML (or SVG) then that option should be handled. For now, the 
        rasterized images will be placed in-line. This accepts either Nodes or 
        NodeLists and handles all instances of <inline-formula> beneath them'''
        try:
            inline_formulas = topnode.getElementsByTagName('inline-formula')
        except AttributeError:
            for item in topnode:
                self.inlineFormulaNodeHandler(topnode, doc)
        else:
            #There is a potential for complexity of content within the
            #<inline-formula> tag. I have supplied methods for collecting the 
            #complex matter, but do not yet implement its inclusion
            for if_node in inline_formulas:
                parent = if_node.parentNode
                sibling = if_node.nextSibling
                
                #Potential Attributes
                if_alt_form_of = if_node.getAttribute('alternate-form-of')
                try:
                    if_node.removeAttribute('alternate-form-of')
                except xml.dom.NotFoundErr:
                    pass
                if_id = if_node.getAttribute('id')
                
                #Handle the conversion of emphasis elements
                #if_node = utils.getFormattedNode(if_node)
                
                #Potential contents
                if_private_char = if_node.getElementsByTagName('private-char')
                if_tex_math = if_node.getElementsByTagName('tex-math')
                if_mml_math = if_node.getElementsByTagName('mml:math')
                if_inline_formula = if_node.getElementsByTagName('inline-formula')
                if_sub = if_node.getElementsByTagName('sub')
                if_sup = if_node.getElementsByTagName('sup')
                
                #Collect the inline-graphic element, which we will try to use 
                #in order to create an image node
                if_inline_graphic = if_node.getElementsByTagName('inline-graphic')
                img = None
                if if_inline_graphic:
                    ig_node = if_inline_graphic[0]
                    xlink_href_id = ig_node.getAttribute('xlink:href')
                    name = xlink_href_id.split('.')[-1]
                    img = None
                    startpath = os.getcwd()
                    os.chdir(self.outdir)
                    for path, _subdirs, filenames in os.walk('images-{0}'.format(self.jid)):
                        for filename in filenames:
                            if os.path.splitext(filename)[0] == name:
                                img = os.path.join(path, filename)
                    os.chdir(startpath)
                if img:
                    imgnode = doc.createElement('img')
                    imgnode.setAttribute('src', img)
                    imgnode.setAttribute('alt', 'An inline formula')
                    parent.insertBefore(imgnode, sibling)
                
                parent.removeChild(if_node)
    
    def dispFormulaNodeHandler(self, topnode, doc):
        '''Handles disp-formula nodes'''
        try:
            disp_formulas = topnode.getElementsByTagName('disp-formula')
        except AttributeError:
            for item in topnode:
                self.dispFormulaNodeHandler(item, doc)
        else:
            for disp in disp_formulas:
                attrs = {'id': None, 'alternate-form-of': None}
                for attr in attrs:
                    attrs[attr] = disp.getAttribute(attr)
                
                try:
                    graphic = disp.getElementsByTagName('graphic')[0]
                except IndexError:
                    logging.error('disp-formula element does not contain graphic element')
                else:
                    graphic_xlink_href = graphic.getAttribute('xlink:href')
                    if not graphic_xlink_href:
                        logging.error('graphic xlink:href attribute not present for disp-formula')
                    else:
                        name = graphic_xlink_href.split('.')[-1]
                        img = None
                        startpath = os.getcwd()
                        os.chdir(self.outdir)
                        for path, _subdirs, filenames in os.walk('images-{0}'.format(self.jid)):
                            for filename in filenames:
                                if os.path.splitext(filename)[0] == name:
                                    img = os.path.join(path, filename)
                        os.chdir(startpath)
                        
                        #Convert <label> to <b class="disp-form-label">
                        #Also move it up a level, after the formula
                        for item in disp.getElementsByTagName('label'):
                            disp.parentNode.insertBefore(item, disp.nextSibling)
                            item.tagName = 'b'
                            item.setAttribute('class', 'disp-formula-label')
                        
                        img_node = doc.createElement('img')
                        img_node.setAttribute('src', img)
                        img_node.setAttribute('alt', 'A display formula')
                        img_node.setAttribute('class', 'disp-formula')
                        parent = disp.parentNode
                        parent.insertBefore(img_node, disp)
                        parent.removeChild(disp)
                        
    
    def tableWrapNodeHandler(self, topnode, doc, tabdoc):
        '''Handles conversion of <table-wrap> tags under the provided topnode. 
        Also handles NodeLists by calling itself on each Node in the NodeList. 
        Must be compliant with the Journal Publishing Tag Set 2.0 and produce 
        OPS 2.0.1 compliant output. HTML versions of tables will be exported to
        tables.xml and must be fully HTML compliant'''
        try:
            table_wraps = topnode.getElementsByTagName('table-wrap')
        except AttributeError:
            for item in topnode:
                self.tableWrapNodeHandler(item, doc)
        else:
            for tab_wrap in table_wraps:
                #These are in order
                tab_object_id = tab_wrap.getElementsByTagName('object-id') #zero or more
                tab_label = tab_wrap.getElementsByTagName('label') #zero or one
                tab_caption = tab_wrap.getElementsByTagName('caption') #zero or one
                #Accessibility Elements ; Any combination of
                tab_alt_text = tab_wrap.getElementsByTagName('alt-text')
                tab_long_desc = tab_wrap.getElementsByTagName('long-desc')
                #Address Linking Elements ; Any combination of
                tab_email = tab_wrap.getElementsByTagName('email')
                tab_ext_link = tab_wrap.getElementsByTagName('ext-link')
                tab_uri = tab_wrap.getElementsByTagName('uri')
                #Document location information
                tab_parent = tab_wrap.parentNode
                tab_sibling = tab_wrap.nextSibling
                #This should provide the fragment identifier
                tab_id = tab_wrap.getAttribute('id')
                
                if tab_alt_text: #Extract the alt-text if list non-empty
                    tab_alt_text_text = utils.getTagData(tab_alt_text)
                else:
                    tab_alt_text_text = 'A figure'
                    
                if tab_long_desc:
                    tab_long_desc_text = utils.getTagData(tab_long_desc)
                else:
                    tab_long_desc_text = None
                
                #In this case, we will create an <img> node to replace <table-wrap>
                img_node = doc.createElement('img')
                
                #The following code block uses the fragment identifier to
                #locate the correct source file based on PLoS convention
                name = tab_id.split('-')[-1]
                startpath = os.getcwd()
                os.chdir(self.outdir)
                for path, _subdirs, filenames in os.walk('images-{0}'.format(self.jid)):
                    for filename in filenames:
                        if os.path.splitext(filename)[0] == name:
                            img_src = os.path.join(path, filename)
                os.chdir(startpath)
                
                #Now we can begin to process to output
                try:
                    img_node.setAttribute('src', img_src)
                except NameError:
                    print('Image source not found')
                    img_node.setAttribute('src', 'not_found')
                img_node.setAttribute('alt', tab_alt_text_text)
                #The handling of longdesc is important to accessibility
                #Due to the current workflow, we will be storing the text of 
                #longdesc in the optional title attribute of <img>
                #A more optimal strategy would be to place it in its own text
                #file, we need to change the generation of the OPF to do this
                #See http://idpf.org/epub/20/spec/OPS_2.0.1_draft.htm#Section2.3.4
                if tab_long_desc_text:
                    img_node.setAttribute('title', tab_long_desc_text)
                
                #Replace the tab_wrap_node with img_node
                tab_parent.replaceChild(img_node, tab_wrap)
                
                #Handle the table caption if it exists
                tab_caption_title_node = None
                if tab_caption:
                    tab_caption_node = tab_caption[0] #There should only be one
                    tab_caption_title = tab_caption_node.getElementsByTagName('title')
                    if tab_caption_title:
                        tab_caption_title_node = tab_caption_title[0]
                
                #Create a Table header, includes label and title, place before the image
                tab_header = doc.createElement('div')
                tab_header.setAttribute('class', 'table_header')
                tab_header.setAttribute('id', tab_id)
                if tab_label:
                    tab_header_b = doc.createElement('b')
                    for item in tab_label[0].childNodes:
                        tab_header_b.appendChild(item.cloneNode(deep=True))
                    tab_header_b.appendChild(doc.createTextNode(u'. '))
                    tab_header.appendChild(tab_header_b)
                if tab_caption_title_node:
                    for item in tab_caption_title_node.childNodes:
                        tab_header.appendChild(item.cloneNode(deep = True))
                tab_parent.insertBefore(tab_header, img_node)
                
                #Handle email
                for email in tab_email:
                    email.tagName = 'a'
                    text = each.getTagData
                    email.setAttribute('href','mailto:{0}'.format(text))
                    if tab_sibling:
                        tab_parent.insertBefore(email, tab_sibling)
                    else:
                        tab_parent.appendChild(email)
                
                #Handle <table>s: This is an XHTML Table Model (less the <caption>)
                #These text format tables are useful alternatives to the 
                #rasterized images in terms of accessibility and machine-
                #readability. This element should be preserved and placed in
                #tables.xml
                tables = tab_wrap.getElementsByTagName('table')
                tab_first = True
                for table in tables:
                    try:
                        table.removeAttribute('alternate-form-of')
                    except xml.dom.NotFoundErr:
                        pass
                    if tab_first:
                        table.setAttribute('id', tab_id)
                        tab_first = False
                    #Unfortunately, this XHTML Table Model is allowed to have
                    #unorthodox elements... the fooNodeHandler methods may be necessary
                    self.boldNodeHandler(table)
                    self.xrefNodeHandler(table)
                    self.italicNodeHandler(table)
                    
                    #Add the table to the table document
                    tabdoc.appendChild(table)
                
                #Create a link to the HTML table version
                if tables:
                    h_link = doc.createElement('a')
                    h_link.setAttribute('href', self.tab_frag.format(tab_id))
                    h_link.appendChild(doc.createTextNode('HTML version of this table'))
                    tab_parent.insertBefore(h_link, tab_sibling)
                
                #Handle <table-wrap-foot>
                #Because the contents of this element are presented by PLoS in 
                #the rasterized image, it makes little sense to include it in 
                #the text itself, instead we will append it to tables.xml
                tab_wrap_foots = tab_wrap.getElementsByTagName('table-wrap-foot')
                for tab_foot in tab_wrap_foots:
                    foot_div = doc.createElement('div')
                    foot_div.setAttribute('class', 'footnotes')
                    for child in tab_foot.childNodes:
                        foot_div.appendChild(child.cloneNode(deep = True))
                    for fn in foot_div.getElementsByTagName('fn'):
                        fn.tagName = 'div'
                        try:
                            fn.removeAttribute('symbol')
                        except xml.dom.NotFoundErr:
                            pass
                        try:
                            fn.removeAttribute('xml:lang')
                        except xml.dom.NotFoundErr:
                            pass
                        fn_type = fn.getAttribute('fn-type')
                        try:
                            fn.removeAttribute('fn-type')
                        except xml.dom.NotFoundErr:
                            pass
                        for label in foot_div.getElementsByTagName('label'):
                            if utils.getTagText(label):
                                label.tagName = u'b'
                            else:
                                label_parent = label.parentNode
                                label_parent.removeChild(label)
                        for title in foot_div.getElementsByTagName('title'):
                            title.tagName = u'b'
                        for cps in foot_div.getElementsByTagName('copyright-statement'):
                            cps.tagName = u'p'
                        for attr in foot_div.getElementsByTagName('attrib'):
                            attr.tagName = u'p'
                        
                        self.boldNodeHandler(foot_div)
                        self.xrefNodeHandler(foot_div)
                        self.italicNodeHandler(foot_div)
                        
                        tabdoc.appendChild(foot_div)
                        
                #Place a link in the table document that directs back to the main
                m_link = doc.createElement('a')
                m_link.setAttribute('href', self.main_frag.format(tab_id))
                m_link.appendChild(doc.createTextNode('Back to the text'))
                m_link_p = doc.createElement('p')
                m_link_p.appendChild(m_link)
                tabdoc.appendChild(m_link_p)
                #ext-links are currently ignored
                
                #uris are currently ignored
                
                #Fig may contain many more elements which are currently ignored
                #See http://dtd.nlm.nih.gov/publishing/tag-library/2.0/n-un80.html
                #For more details on what could be potentially handled
    
    def boxedTextNodeHandler(self, topnode):
        '''Handles conversion of <boxed-text> tags under the provided topnode. 
        The best semantic approximation for boxed-text elements that I can 
        decide on currently is the blockquote element. Also handles NodeLists 
        by calling itself on each Node in the NodeList.'''
        
        keep_attrs = ['id']
        
        try:
            boxed_texts = topnode.getElementsByTagName('boxed-text')
        except AttributeError:
            for item in topnode:
                self.boxedTextNodeHandler(item)
        else:
            for boxed_text in boxed_texts:
                attrs = {'content-type': None, 'id': None, 
                         'position': None, 'xml:lang': None}
                for attr in attrs:
                    attrs[attr] = boxed_text.getAttribute(attr)
                    if attr not in keep_attrs:
                        try:
                            boxed_text.removeAttribute(attr)
                        except xml.dom.NotFoundErr:
                            pass
                        
                parent = boxed_text.parentNode
                boxed_text.tagName = 'blockquote'
                boxed_text_titles = boxed_text.getElementsByTagName('title')
                for title in boxed_text.getElementsByTagName('title'):
                    title.tagName = u'b'
    
    def supplementaryMaterialNodeHandler(self, topnode, doc):
        '''Handles conversion of <supplementary-material> tags under the 
        provided topnode. Also handles NodeLists by calling itself on each 
        Node in the NodeList.'''
        
        try:
            supp_mats = topnode.getElementsByTagName('supplementary-material')
        except AttributeError:
            for item in topnode:
                self.supplementaryMaterialNodeHandler(item)
        else:
            for supp_mat in supp_mats:
                #http://dtd.nlm.nih.gov/publishing/tag-library/2.0/n-au40.html
                #Provides the details on this node. There are many potential 
                #attributes which are not employed by PLoS, they stick closely  
                #id, mimetype, xlink:href, position, and xlink:type
                #This code will not function fully without a provided id
                #PLoS appears very strict with its inclusion
                
                attrs = {'id': None, 'mimetype': None, 'xlink:href': None, 
                         'position': None, 'xlink:type': None}
                keep_attrs = ['id']
                #A different approach to attribute handling... pack them all 
                #into a dictionary for key access and remove them if not valid 
                #ePub attributes. Retrieve attribute valuse as needed from dict
                for attr in attrs:
                    attrs[attr] = supp_mat.getAttribute(attr)
                    if attr not in keep_attrs:
                        try:
                            supp_mat.removeAttribute(attr)
                        except xml.dom.NotFoundErr:
                            pass
                            
                supp_mat.tagName = 'div' #Convert supplementary-material to div
                
                try:
                    supp_mat_object_id = supp_mat.getElementsByTagName('object-id')[0]
                except IndexError:
                    supp_mat_object_id = None
                else:
                    #We remove this tag and ignore it for now
                    supp_mat.removeChild(supp_mat_object_id)
                
                try: #Convert the label to bold if it exists
                    supp_mat_label = supp_mat.getElementsByTagName('label')[0]
                except IndexError:
                    supp_mat_label = None
                else:
                    supp_mat_label.tagName = u'b'
                    
                try:
                    supp_mat_caption =supp_mat.getElementsByTagName('caption')[0]
                except IndexError:
                    supp_mat_caption = None
                else:
                    supp_mat_caption.tagName = u'div' 
                
                #A mapping of 4-character codes to web addresses
                plos_jrns= {'pgen': 'http://www.plosgenetics.org/', 
                            'pone': 'http://www.plosone.org/', 
                            'pbio': 'http://www.plosbiology.org/', 
                            'pcbi': 'http://www.ploscompbiol.org/', 
                            'ppat': 'http://www.plospathogens.org/', 
                            'pmed': 'http://www.plosmedicine.org/', 
                            'pntd': 'http://www.plosntds.org/'}
                try:
                    jrn = attrs['xlink:href'].split('journal.')[1].split('.')[0]
                except KeyError:
                    print('supplementary-tag tag found without attribute \"xlink:href\"')
                else:
                    fetch = 'article/fetchSingleRepresentation.action?uri='
                    try:
                        xlink = attrs['xlink:href']
                    except KeyError:
                        print('supplementary-tag tag found without attribute \"xlink:href\"')
                    else:
                        href = u'{0}{1}{2}'.format(plos_jrns[jrn], fetch, xlink)
                        anchor = doc.createElement('a')
                        anchor.setAttribute('href', href)
                        if supp_mat_label:
                            supp_mat.insertBefore(anchor, supp_mat_label)
                            anchor.appendChild(supp_mat_label)
                
    def boldNodeHandler(self, topnode):
        '''Handles proper conversion of <bold> tags under the provided 
        topnode. Also handles NodeLists by calling itself on each Node in the 
        NodeList'''
        try:
            bold_nodes = topnode.getElementsByTagName('bold')
            
        except AttributeError:
            for item in topnode:
                self.boldNodeHandler(item)
        else:
            #In this case, we can just modify them in situ
            for bold_node in bold_nodes:
                bold_node.tagName = u'b'

                
    def italicNodeHandler(self, topnode):
        '''Handles proper conversion of <italic> tags under the provided 
        topnode. Also handles NodeLists by calling itself on each Node in the 
        NodeList'''
        try:
            italic_nodes = topnode.getElementsByTagName('italic')
        except AttributeError:
            for item in topnode:
                self.italicNodeHandler(item)
        else:
            #In this case, we can just modify them in situ
            for italic_node in italic_nodes:
                italic_node.tagName = u'i'

    def monospaceNodeHandler(self, topnode):
        '''Handles proper conversion of <monospace> tags under the provided 
        topnode. Also handles NodeLists by calling itself on each Node in the 
        NodeList'''
        try:
            monospace_nodes = topnode.getElementsByTagName('monospace')
        except AttributeError:
            for item in topnode:
                self.monospaceNodeHandler(item)
        else:
            #In this case, we can just modify them in situ
            for mono_node in monospace_nodes:
                mono_node.tagName = u'span'
                mono_node.setAttribute('style', 'font-family:monospace')
                
    def dispQuoteNodeHandler(self, topnode, doc):
        '''Handles proper conversion of <disp-quote> tags under the provided 
        topnode. Also handles NodeLists by calling itself on each Node in the 
        NodeList'''
        try:
            disp_quote_nodes = topnode.getElementsByTagName('disp-quote')
        except AttributeError:
            for item in topnode:
                self.dispQuoteNodeHandler(item, doc)
        else:
            for disp in disp_quote_nodes:
                
                attrs = {'content-type': None, 'id': None, 
                         'specific-use': None, 'xml:lang': None}
                for attr in attrs:
                    attrs[attr] = disp.getAttribute(attr)
                    try:
                        disp.removeAttribute(attr)
                    except xml.dom.NotFoundErr:
                        pass
                    
                    disp.tagName = u'span'
                    disp.setAttribute('class', 'disp-quote')
                    disp_ps = disp.getElementsByTagName('p')
                    first = True
                    for disp_p in disp_ps:
                        if not first:
                            disp.insertBefore(doc.createElement('br'), disp_p)
                        for child in disp_p.childNodes:
                            disp.insertBefore(child, disp_p)
                        disp.removeChild(disp_p)
                        first = False
                        
                    #parent = disp.parentNode
                    #grandparent = parent.parentNode
                    #disp_index = parent.childNodes.index(disp)
                    #parent_sibling = parent.nextSibling
                    
                    #disp_p = doc.createElement('p')
                    #grandparent.insertBefore(disp_p, parent_sibling)
                    #new_p = doc.createElement('p')
                    #grandparent.insertBefore(new_p, parent_sibling)
                    #for each in parent.childNodes[disp_index + 1:]:
                    #    new_p.appendChild(each)
                        
                    #Now that we have modified the structure, modify the tag
                    #and it's children:
                    
    
    def subNodeHandler(self, topnode):
        '''Handles the potential attribute \"arrange\" for sub elements under 
        the provided Node. Also handles NodeLists by calling itself on each 
        Node in the NodeList'''
        try:
            sub_nodes = topnode.getElementsByTagName('sub')
        except AttributeError:
            for item in topnode:
                self.subNodeHandler(item)
        else:
            for sub_node in sub_nodes:
                arrange = sub_node.getAttribute('arrange')
                if arrange:
                    sub_node.removeAttribute('arrange')
                    sub_node.setAttribute('class', arrange)
    
    def supNodeHandler(self, topnode):
        '''Handles the potential attribute \"arrange\" for sup elements under 
        the provided Node. Also handles NodeLists by calling itself on each 
        Node in the NodeList'''
        try:
            sup_nodes = topnode.getElementsByTagName('sup')
        except AttributeError:
            for item in topnode:
                self.subNodeHandler(item)
        else:
            for sup_node in sup_nodes:
                arrange = sup_node.getAttribute('arrange')
                if arrange:
                    sup_node.removeAttribute('arrange')
                    sup_node.setAttribute('class', arrange)
    
    def smallCapsNodeHandler(self, topnode):
        '''Handles proper conversion of <sc> tags under the provided 
        topnode. Also handles NodeLists by calling itself on each Node in the 
        NodeList'''
        try:
            sc_nodes = topnode.getElementsByTagName('sc')
        except AttributeError:
            for item in topnode:
                self.smallCapsNodeHandler(item)
        else:
            #In this case, we can just modify them in situ
            for sc_node in sc_nodes:
                sc_node.tagName = u'span'
                sc_node.setAttribute('style', 'font-variant:small-caps')
    
    def underlineNodeHandler(self, topnode):
        '''Handles proper conversion of <underline> tags under the provided 
        topnode. Also handles NodeLists by calling itself on each Node in the 
        NodeList'''
        try:
            underline_nodes = topnode.getElementsByTagName('underline')
        except AttributeError:
            for item in topnode:
                self.underlineNodeHandler(item)
        else:
            #In this case, we can just modify them in situ
            for underline_node in underline_nodes:
                underline_node.tagName = u'span'
                underline_node.setAttribute('style', 'text-decoration:underline')
    
    def namedContentNodeHandler(self, topnode):
        '''Handles the <named-content> tag. This method needs development to 
        fit PLoS practice. Handles NodeLists by calling itself on each Node in 
        the NodeList'''
        
        #The content-type attribute can be used to identify the subject or type 
        #of content that makes this word or phrase semantically special and, 
        #therefore, to be treated differently. For example, this attribute 
        #could be used to identify a drug name, company name, or product name. 
        #It could be used to define systematics terms, such as genus, family, 
        #order, or suborder. It could also be used to identify biological 
        #components, such as gene, protein, or peptide. It could be used to 
        #name body systems, such as circulatory or skeletal. Therefore, values 
        #may include information classes, semantic categories, or types of 
        #nouns such as "generic-drug-name", "genus-species", "gene", "peptide", 
        #"product", etc.
        
        try:
            namedcontent_nodes = topnode.getElementsByTagName('named-content')
        except AttributeError:
            for item in topnode:
                self.namedContentNodeHandler(item)
        else:
            #In this case, we modify them in situ
            for nc_node in namedcontent_nodes:
                nc_content_type = nc_node.getAttribute('content-type')
                try:
                    nc_node.removeAttribute('content-type')
                except xml.dom.NotFoundErr:
                    pass
                nc_id = nc_node.getAttribute('id')
                nc_xlink_actuate = nc_node.getAttribute('xlink:actuate')
                try:
                    nc_node.removeAttribute('xlink:actuate')
                except xml.dom.NotFoundErr:
                    pass
                nc_xlink_href = nc_node.getAttribute('xlink:href')
                try:
                    nc_node.removeAttribute('xlink:href')
                except xml.dom.NotFoundErr:
                    pass
                nc_xlink_role = nc_node.getAttribute('xlink:role')
                try:
                    nc_node.removeAttribute('xlink:role')
                except xml.dom.NotFoundErr:
                    pass
                nc_xlink_show = nc_node.getAttribute('xlink:show')
                try:
                    nc_node.removeAttribute('xlink:show')
                except xml.dom.NotFoundErr:
                    pass
                nc_xlink_title = nc_node.getAttribute('xlink:title')
                try:
                    nc_node.removeAttribute('xlink:title')
                except xml.dom.NotFoundErr:
                    pass
                nc_xlink_type = nc_node.getAttribute('xlink:type')
                try:
                    nc_node.removeAttribute('xlink:type')
                except xml.dom.NotFoundErr:
                    pass
                nc_xmlns_xlink = nc_node.getAttribute('xmlns:xlink')
                try:
                    nc_node.removeAttribute('xmlns:xlink')
                except xml.dom.NotFoundErr:
                    pass
                
                #Current approach: convert to <span style="content-type">
                nc_node.tagName = u'span'
                nc_node.setAttribute('style', nc_content_type)
        
    
    def secNodeHandler(self, topnode):
        '''Handles proper conversion of <sec> tags under the provided topnode.
        Also handles NodeLists by calling itself on each Node in the NodeList. 
        '''
        try:
            sec_nodes = topnode.getElementsByTagName('sec')
        except AttributeError:
            for item in topnode:
                self.secNodeHandler(item)
        else:
            #In this case, we can just modify them in situ
            c = 0
            for sec_node in sec_nodes:
                sec_node.tagName = u'div'
                try:
                    sec_node.removeAttribute('sec-type')
                except xml.dom.NotFoundErr:
                    pass
                if not sec_node.getAttribute('id'):
                    id = 'OA-EPUB-{0}'.format(str(c))
                    c += 1
                    sec_node.setAttribute('id', id)
    
    def xrefNodeHandler(self, topnode):
        '''Handles conversion of <xref> tags. These tags are utilized for 
        internal crossreferencing. Works on all tags under the provided Node 
        or under all Nodes in a NodeList.'''
        
        #We need mappings for local files to ref-type attribute values
        ref_map = {u'bibr': self.bib_frag,
                   u'fig': self.main_frag,
                   u'supplementary-material': self.main_frag,
                   u'table': self.main_frag,
                   u'aff': self.syn_frag,
                   u'sec': self.main_frag,
                   u'table-fn': self.tab_frag,
                   u'boxed-text': self.main_frag,
                   u'other': self.main_frag,
                   u'disp-formula': self.main_frag}
        
        try:
            xref_nodes = topnode.getElementsByTagName('xref')
        except AttributeError:
            for item in topnode:
                self.xrefNodeHandler(item)
        else:
            for xref_node in xref_nodes:
                xref_node.tagName = u'a' #Convert to <a> tag
                #Handle the ref-type attribute
                ref_type = xref_node.getAttribute('ref-type')
                xref_node.removeAttribute('ref-type')
                #Handle the rid attribute
                rid = xref_node.getAttribute('rid')
                xref_node.removeAttribute('rid')
                #Set the href attribute
                href = ref_map[ref_type].format(rid)
                xref_node.setAttribute('href', href)
                
    
    def emailNodeHandler(self, topnode):
        '''Handles conversion of <email> tags underneath the provided Node 
        or NodeList.'''
        
        try:
            emails = topnode.getElementsByTagName('email')
        except AttributeError:
            for item in topnode:
                self.emailNodeHandler(item)
        else:
            for email in emails:
                attrs = {'xlink:actuate': None, 'xlink:href': None, 
                         'xlink:role': None, 'xlink:show': None, 
                         'xlink:title': None, 'xlink:type': None, 
                         'xmlns:xlink': None}
                for attr in attrs:
                    attrs[attr] = email.getAttribute(attr)
                    try:
                        email.removeAttribute(attr)
                    except xml.dom.NotFoundErr:
                        pass
                email.tagName = u'a'
                address = utils.getTagText(email)
                href = u'mailto:{0}'.format(address)
                email.setAttribute('href', href)
    
    def fnNodeHandler(self, topnode):
        '''Handles conversion of <fn> tags where encountered under the 
        provided topnode. These are used for footnotes, so the general idea is 
        to convert their tagname and give them a class attribute'''
        keep_attrs = ['id']
        
        try:
            fns = topnode.getElementsByTagName('fn')
        except AttributeError:
            for item in fns:
                self.fnNodeHandler(item)
        else:
            for fn in fns:
                fn.tagName = u'span'
                #Handle the potential attributes
                attrs = {'fn-type': None, 'id': None, 'symbol': None, 
                         'xml:lang': None}
                for attr in attrs:
                    if attr not in keep_attrs:
                        try:
                            fn.removeAttribute(attr)
                        except xml.dom.NotFoundErr:
                            pass
                #Assign the class attribute to "footnote"
                fn.setAttribute('class', 'footnote')
                #If there is a <p> tag inside, take it's children and remove <p>
                fn_ps = fn.getElementsByTagName('p')
                for fn_p in fn_ps:
                    for child in fn_p.childNodes:
                        fn.insertBefore(child, fn_p)
                    fn.removeChild(fn_p)
    
    def extLinkNodeHandler(self, topnode):
        '''Handles conversion of <ext-link> tags. These tags are utilized for 
        external referencing. Works on all tags under the provided Node or 
        under all Nodes in a NodeList.'''
        
        keep_attrs = ['id']
        
        try:
            ext_links = topnode.getElementsByTagName('ext-link')
        except AttributeError:
            for item in topnode:
                self.extLinkNodeHandler(item)
        else:
            for ext_link in ext_links:
                ext_link.tagName = u'a' #convert to <a>
                #Handle the potential attributes
                attrs = {'ext-link-type': None, 'id': None,
                         'xlink:actuate': None, 'xlink:href': None,
                         'xlink:role': None, 'xlink:show': None,
                         'xlink:title': None, 'xlink:type': None,
                         'xmlns:xlink': None}
                
                for attr in attrs:
                    attrs[attr] = ext_link.getAttribute(attr)
                    if attr not in keep_attrs:
                        try:
                            ext_link.removeAttribute(attr)
                        except xml.dom.NotFoundErr:
                            pass
                    #Set the href value from the xlink:href
                    if attrs['xlink:href']:
                        ext_link.setAttribute('href', attrs['xlink:href'])
                    
                    #Logging and Debug section
                    if not attrs['ext-link-type'] == u'uri':
                        logging.info('<ext-link> attribute \"ext-link-type\" = {0}'.format(attrs['ext-link-type']))
                    if not attrs['xlink:type'] == u'simple':
                        logging.info('<ext-link> attribute \"xlink:type\" = {0}'.format(attrs['xlink:type']))
    
    def listNodeHandler(self, topnode, doc):
        '''Handles conversion of <list> tags which are used to represent data
        in either a linked fashion with or without linear order. Finds all
        <list> elements under the provided Node; also works on NodeLists by
        calling itself on each element in the list'''
        
        types = {'order': 'ol', 'bullet': 'ul', 'alpha-lower': 'ol', 
                 'alpha-upper': 'ol', 'roman-lower': 'ol', 'roman-upper': 'ol', 
                 'simple': 'ul', '': 'ul'}
        
        try: 
            lists = topnode.getElementsByTagName('list')
        except AttributeError:
            for item in topnode:
                self.listNodeHandler(item, doc)
        else:
            for list in lists:
                
                parent = list.parentNode
                grandparent = parent.parentNode
                list_index = parent.childNodes.index(list)
                parent_sibling = parent.nextSibling
                
                if parent.tagName == 'p':
                    grandparent.insertBefore(list, parent_sibling)
                    new_p = doc.createElement('p')
                    grandparent.insertBefore(new_p, parent_sibling)
                    for each in parent.childNodes[list_index + 1:]:
                        new_p.appendChild(each)
                
                attrs = {'id': None, 'list-content': None, 'list-type': None, 
                         'prefix-word': None}
                
                #Collect all attribute values into dict and remove from DOM
                for attr in attrs:
                    attrs[attr] = list.getAttribute(attr)
                    try:
                        list.removeAttribute(attr)
                    except xml.dom.NotFoundErr:
                        pass
                
                try: #A list has zero or one title elements
                    list_title_node = list.getElementsByTagName('list')[0]
                except IndexError:
                    list_title_node = None
                else: #Do something with the title element
                    list.setAttribute('title', utils.serializeText(list_title_node))
                    list.removeChild(list_title_node)
                
                try: #Set tagName as mapped in types{} based on list-type value
                    list.tagName = types[attrs['list-type']]
                except KeyError:
                    logging.warning('unknown list-type value found: {0}'.format(attrs['list-type']))
                    list.tagName = 'ul'
                    list.setAttribute('style', 'simple')
                
                #Lists can be stacked: we cannot simply use getElementsByTagName
                
                list_items = []
                for child in list.childNodes:
                    try:
                        if child.tagName == 'list-item':
                            list_items.append(child)
                    except AttributeError:
                        pass
                
                for list_item in list_items:
                    list_item.tagName = u'li'
                
    
    def graphicNodeHandler(self, topnode):
        '''Handles rudimentary conversion of <graphic> tags. Typically when 
        found when not enclosed in any other structure. Finds all <graphic> 
        tags under the provided topnode. Also works on NodeLists by calling 
        itself on each node in the NodeList.'''
        
        #<graphic> elements are commonly found in special contexts:
        #In those cases, decide if this method provides the needed support
        #or if special handling is needed.
        try:
            graphics = topnode.getElementsByTagName('graphic')
        except AttributeError:
            for item in topnode:
                self.graphicNodeHandler()
        else:
            for graphic in graphics:
                #Handle graphic Attributes
                attrs = {'alt-version': None, 'alternate-form-of': None, 
                         'id': None, 'mime-subtype': None, 'mimetype': None, 
                         'position': None, 'xlink:actuate': None, 
                         'xlink:href': None, 'xlink:role': None, 
                         'xlink:title': None, 'xlink:type': None, 
                         'xmlns:xlink': None}
                for attr in attrs:
                    attrs[attr] = graphic.getAttribute(attr)
                    try:
                        graphic.removeAttribute(attr)
                    except xml.dom.NotFoundErr:
                        pass
                
                name = attrs['xlink:href'].split('.')[-1]
                img = None
                startpath = os.getcwd()
                os.chdir(self.outdir)
                for path, _subdirs, filenames in os.walk('images-{0}'.format(self.jid)):
                    for filename in filenames:
                        if os.path.splitext(filename)[0] == name:
                            img = os.path.join(path, filename)
                os.chdir(startpath)
                
                #modify the <graphic> tag to <img>
                if img:
                    graphic.tagName = 'img'
                    graphic.setAttribute('src', img)
                else:
                    logging.error('graphicNodeHandler: Image source not found')
    
    
    def divTitleFormat(self, fromnode, depth = 0):
        '''A method for converting title tags to heading format tags'''
        taglist = ['h2', 'h3', 'h4', 'h5', 'h6']
        for item in fromnode.childNodes:
            try:
                tag = item.tagName
            except AttributeError:
                pass
            else:
                if item.tagName == u'div':
                    try:
                        divtitle = item.getElementsByTagName('title')[0]
                    except IndexError:
                        pass
                    else:
                        if not divtitle.childNodes:
                            item.removeChild(divtitle)
                        else:
                            divtitle.tagName = taglist[depth]
                        depth += 1
                        self.divTitleFormat(item, depth)
                        depth -= 1

    def initiateDocument(self, titlestring):
        '''A method for conveniently initiating a new xml.DOM Document'''
        
        impl = minidom.getDOMImplementation()
        
        mytype = impl.createDocumentType('html', 
                                         '-//W3C//DTD XHTML 1.1//EN', 
                                         'http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd')
        doc = impl.createDocument(None, 'html', mytype)
        
        root = doc.lastChild #IGNORE:E1101
        root.setAttribute('xmlns', 'http://www.w3.org/1999/xhtml')
        root.setAttribute('xml:lang', 'en-US')
        
        head = doc.createElement('head')
        root.appendChild(head)
        
        title = doc.createElement('title')
        title.appendChild(doc.createTextNode(titlestring))
        
        link = doc.createElement('link')
        link.setAttribute('rel', 'stylesheet')
        link.setAttribute('href','css/article.css')
        link.setAttribute('type', 'text/css')
        
        meta = doc.createElement('meta')
        meta.setAttribute('http-equiv', 'Content-Type')
        meta.setAttribute('content', 'application/xhtml+xml')
        
        headlist = [title, link, meta]
        for tag in headlist:
            head.appendChild(tag)
        root.appendChild(head)
        
        body = doc.createElement('body')
        root.appendChild(body)
        
        return doc, body
