Glossary
--------

.. glossary::
  :sorted:

  Central concept
    The ‘central’ meaning among all forms that derive from the same etymological root.
    This can be a the reconstructed meaning of the root in a proto-language, but it can e.g. also be a less rigid shorthand for the central meaning of polysemous forms.
    Central concepts can be assigned manually, or automatically using :py:mod:`lexedata.edit.add_central_concepts`. For the automatic assignment, lexedata uses the colexification patterns present in the `CLICS database <https://clics.clld.org>`_.

    .. seealso:: :term:`central concept AH`

  Central concept AH
    An absence heuristic.
    One of two ways to assign absences in the case of :term:`root presence coding`, based on assigning each cross-concept cognate set to a concept (the central concept).
    Then, a ``0`` would be coded if the :term:`central concept` of a :term:`cross-concept cognate set` is expressed by a different root. This is the same as the way absences are assigned with the :term:`root-meaning coding` method. The results are however different, since in root presence coding items that have undergone semantic shift are included thus forming a less "sparse" matrix. Central concepts are in this operation treated as the most likely concept where a reflex of a form would be found. If they are expressed with a different root, then we conclude that the root in question must be absent.

    .. seealso:: :term:`half primary concepts AH`

  Phylogenetic coding method
    The method used to derive a character matrix that can be used as input for phylogenetic analyses.
    There are three main coding methods for lexical data that have been used for phylogenetic analyses. We will briefly list them here.

    1. :term:`root-meaning coding`
    2. :term:`root presence coding`
    3. :term:`multistate coding`

  Cross-concept cognate set
    A cognate set that includes all descendants or reflexes of a protoform irrespective of their meaning (i.e. including items that have undergone semantic shift). In traditional historical linguistics words are termed cognate if they share a common protoform and they have been passed down to daughter languages from a common ancestor through vertical transmission (i.e. no borrowing has occured). According to this definition, while it is expected that the meaning of cognate words is related, it doesn't have to be identical. In many phylogenetic studies the term "cognate set" has been used for sets of words that derive from a common protoform and additionally have the same meaning. In this manual we are explicit by distinguishing between cross-concept cognate sets and within-concept cognate sets. Lexedata can work with both, but there are some functionalities that only make sense with a particular kind of cognate sets. Also, keep in mind that once cross-concept cognate sets are constructed, then the derivation of within-concept cognate sets is trivial (and lexedata can do it automatically).
    
    .. seealso:: :term:`within-concept cognate set`
    
  NA form
    An NA form is a special type of null (non-existent) form corresponding to a concept not present in the language in question and it is represented with a dash ``-``. For example, it is possible that terms for particular species of flora and fauna, or even for natural phenomena, such as snow, do not exist in a language. Another case could be color terms. In a dataset, it is possible that a concept is present in some languages, but not in others. An NA form conveys that the concept is not applicable to this language. It is in this way distinct from missing data, i.e. that we do not know the corresponding form for this concept in this language (but we assume there is one). NA forms are treated the same as missing data in many cases, but not all. In root-meaning coding, an NA form leads to absences ``0`` to all associated cognate sets, while a missing form leads to ``?``.  

  Primary Concept
    A concept that has been systematically searched for in the languages of the dataset. When building a lexical dataset, it is typical procedure to start with a comparative wordlist including a number of basic concepts (e.g. a Swadesh list). Within lexedata, we call such concepts primary. Any other concepts present in parameters.csv are secondary. A dataset with within-concept cognate sets, often contains only primary concepts (however, it is possible that one has been keeping track of additional meanings for each word, thus leading to the inclusion of a number of secondary concepts as well.). A dataset with cross-concept cognate sets is very likely to include secondary concepts, especially if one has searched for cognate forms extensively among synonyms or closely related concepts to the primary concepts. Primary concepts matter for specific operations in lexedata. You can either provide a list of primary concepts or generate it through lexedata.report.filter if you have primary concepts annotated in your ParameterTable.

    .. seealso:: :term:`half primary concepts AH`, :term:`Secondary Concept`

     .. seealso:: :term:`secondary concept`

  Export
    Lexedata is CLDF-centric, so ‘export’ is always ‘away from CLDF’.

  Half primary concepts AH
    An absence heuristic.
    One of two ways to assign absences for root presence coding, based each :term:`primary concept` associated with the root in question (for all languages in a dataset), instead of privileging one of them (the :term:`central concept`).

    More precisely, a root is deemed absent when at least half of the primary concepts associated with this root are expressed by other roots for a given language. For example, a cross-concept cognate set may include items that mean (in different languages) HEAD, HAIR, and TOP OF THE HEAD. Let us assume that HEAD and HAIR were among the primary concepts, while TOP OF THE HEAD was not.
    Then for a given language the root in question would be coded as absent if at least one (half of the two) primary concepts HEAD and HAIR is expressed by a *different* root.
    Only if we don't know terms for both HEAD and HAIR in this language – or generally, if more than half of the primary concepts associated to the root are missing –, then the root in question would be assigned a ``?``. 
    
    .. seealso :term:`central concept ah`

  Import
    Lexedata is CLDF-centric, so ‘import’ is always ‘towards CLDF’.

  Missing form
    A missing form is a special type of null (non-existent) form representing explicit missing data in the dataset and it has an empty form field (``""``).
    There are in total three types of null forms that can be represented a dataset:

    * missing forms: These forms have been searched for and are unknown according to a sources. They are represented as form row with an empty #form column in the dataset.
    * not-entered forms: These forms do not have any representation in the dataset and correspond to data not yet retrieved or searched for in sources.
    * :term:`NA form`-s, with form ``-``
      
  Multistate coding
    One of three :term:`phylogenetic coding method`'s implemented in lexedata. In this coding method, each :term:`primary concept` corresponds to a multistate character, with each within-concept cognate set corresponding to a different state. It is available for datasets with either within- or cross-concept cognate sets.

  Root-meaning coding
    One of three coding methods implemented in lexedata. This coding method converts every within-concept cognate set in the dataset into a binary character (with 1 representing presence of this root-meaning association in a particular language and 0 absence). When a root-meaning association is not attested in a language, the character is coded as 0 if the meaning in question is expressed with a different root, and as ? if the meaning is not attested at all. The root-meaning coding method can be used for datasets with either cross-concept or within-concept cognate sets.
    
    .. seealso:: :term:`phylogenetic coding method`

  Root presence coding
    One of three :term:`phylogenetic coding method`'s implemented in lexedata. This coding method converts every cross-concept cognate set in the dataset into a binary character (with 1 denoting presence of a reflex of this root in the language and 0 absence). It can be used only when the dataset contains cross-concept cognatesets. Strictly speaking, any non-attestation of a reflex of a particular root in a language should lead to a ?, since we can almost never be sure that a root is indeed absent and it doesn't survive in some marginal meaning. This is even more true in cases of language families that have not been intensively studied. However, a character matrix consisting of 1s and ?s is not informative for phylogenetic analyses, so we need a heuristic to convert in a principled way some of these question marks to absencies. Lexedata provides two absence heuristics:

    1. :term:`central concept ah`
    2. :term:`half primary concepts ah`

  Secondary Concept
    Any concept that has not been systematically searched for in the languages of the dataset. When building a lexical dataset, it is typical procedure to start with a comparative wordlist including a number of basic concepts (e.g. a Swadesh list). Within lexedata, we call such concepts, that have been systematically searched for, primary. Additionaly secondary concepts may be present in a dataset for various reasons: they may be secondary meanings of basic forms or correspond to forms that are cognate to other basic forms. A dataset with within-concept cognate sets, often contains only primary concepts (however, it is possible that one has been keeping track of additional meanings for each word, thus leading to the inclusion of a number of secondary concepts as well.). A dataset with cross-concept cognate sets is very likely to include secondary concepts, especially if one has searched for cognate forms extensively among synonyms or closely related concepts to the primary concepts. 
    
    .. seealso:: :term:`primary concept`

  Segment_Slice column
    Segment_Slice is a column of the CognateTable that can be used to identify a particular section of the form, so that different parts of the form can be assigned to different cognate sets.
    This is part of the `CLDF standard <https://cldf.clld.org/v1.0/terms.html#segmentSlice>`_.

  Status column
    A tracking column present in any of the cldf tables in order to facilitate workflow. Lexedata scripts can also update such columns with customizable messages to facilitate manual checking and tracking of automatic operations.
    This column is not part of `the current v1.1 of the CLDF standard <https://cldf.clld.org/v1.0/terms.html#segmentSlice>`_, which will treat it just as any other text column.

  Within-concept cognate set
    A cognate set that includes descendants or reflexes of a protoform that additionally have the same meaning. While in traditional historical linguistics words are termed cognate if they share a common protoform irrespective of their meaning, in many phylogenetic studies the term "cognate set" has been used for sets of words that not only share an ancestral protoform but all express the same concept. In this manual we are explicit by distinguishing between cross-concept cognate sets and within-concept cognate sets. Lexedata can work with both, but there are some functionalities that only make sense with a particular kind of cognate sets. Also, keep in mind that cross-concept cognate sets cannot be automatically derived from within-concept cognate sets (since this requires linguistic expertise), while the reverse is possible.
    
    .. seealso:: :term:`cross-concept cognate set`
