import type { CheckHelpContent, CheckHelpData } from "../types";

// Helper function to generate check titles
const getCheckTitle = (domainIndex: number, checkIndex: number): string => {
  return `Check ${domainIndex + 1}.${checkIndex + 1}`;
};

export const checkHelpContent: CheckHelpData = {
  // Post-publication Notices (1.1, 1.2, 1.3)
  "postPublication-0": {
    title: getCheckTitle(0, 0), // Check 1.1
    guidelines: `• Reviewers should check whether the publication or publications describing the study have been retracted. Retractions highlight that there is a significant issue with the publication, such that the journal no longer stands by the article; once retracted, an article should no longer be considered part of the published record (9). The Committee for Publication Ethics provides guidelines on the reasons for retraction (10) though be aware that the content of retraction notices can be limited and not representative of all the journal's concerns relating to the reasons for retraction (11).

• In rare instances, an article might be removed or withdrawn, rather than retracted, meaning that the article itself should no longer be available (9). This may occur when there has been a breach of confidentiality, publication of libellous content, or copyright or Intellectual Property infringement (for example) (9). Removed or withdrawn articles should be treated in the same manner as retracted articles when using INSPECT-SR.

• If a study report is retracted, it should be marked as such on the journal website, but not removed, and there should be a separate published retraction notice, also with a unique Digital Object Identifier (DOI). It is important to note that these processes may not be carried out in a systematic fashion across all journals nor indexed well by bibliographic databases.

• Checking for retractions should be performed by accessing the online version of the publication on the journal website, where online notices may be found which have not been indexed elsewhere, and by searching the Retraction Watch database http://retractiondatabase.org/, which is the largest and most reliable database of retractions (12). Be aware that there may be typographic errors in the Retraction Watch database, so DOI may be more useful for searching. Reviewers should confirm that they are searching the Retraction Watch database rather than the associated Retraction Watch blog (i.e. that they are not using the search function at https://retractionwatch.com/ - this does not perform a search of the Retraction Watch database and is not a suitable approach to conducting this check).

• It is recommended to repeat the search shortly before finishing the systematic review, to identify any retractions issued during the conduct of the review.

• Further guidance for searching for post-publication amendments, including retractions, is included in the Cochrane Handbook for Systematic Reviews of Interventions (13) and its associated technical supplement (https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-04-technical-supplement-searching-and-selecting-studies). You may wish to consult with an Information Specialist if further assistance is needed.

• An answer of "yes" for this check would typically warrant a judgement of "serious concerns" for this domain and overall for the index study (i.e., the reviewer would not need to continue with other INSPECT-SR checks), regardless of the reason for retraction and particularly if it was for the main results paper. If the main results paper associated with a study has been retracted, a judgement of "serious concerns" will typically be warranted, regardless of the reason for the retraction. An exception would be where a study has been retracted and subsequently replaced by a new version (e.g. to correct an error). The replacement can then be assessed using INSPECT-SR.`,
    example: `While assessing a clinical trial of a probiotic supplement for gestational diabetes, a systematic reviewer navigates to the journal website. The article has been replaced with a retraction notice, noting that an external statistical review had been performed on the basis of "significant concerns…about the integrity of the data" raised by a third party. The notice states "the main outcome of the external review was that the article's conclusions are unreliable". The reviewer answers "yes" for this check, and this is sufficient to assign a judgement of "serious concerns" for the domain and for the study.`,
  },

  "postPublication-1": {
    title: getCheckTitle(0, 1), // Check 1.2
    guidelines: `• Reviewers should check whether the publication or publications describing the study have associated expressions of concern or other post publication notices. Expressions of concern and other post publication notices, such as notifications, publisher notes, editor notes, etc., are not used and published as consistently as retractions. Expressions of concern are generally used when there are concerns raised about a publication but the evidence is inconclusive or the issue unresolved. Other notifications may be used to flag a potential issue or provide status updates (9).

• Because of this variability, the content and purpose of the notice should be carefully considered when making a judgement. Similarly to retractions, be aware that the content of expressions of concern or other notifications can also be limited and not representative of all the journal's concerns relating to the issue.

• If the notice indicates that there is an ongoing investigation then it is recommended that reviewers revisit the journal website to check for any updates prior to finishing the systematic review.

• Expressions of concern can be checked while looking at whether publications associated with the study have been retracted, by checking the journal website and Retraction Watch database (http://retractiondatabase.org/).

• In addition to post-publication amendments and notices issued by journals or publishers, post-publication comments and critiques posted by researchers in the form of letters to the editor or posts on PubPeer (for example) relating to trustworthiness should also be considered. It is recommended to look for correspondence relating to the trial publication by citation searching in Web of Science or Scopus relating to the journal of trial publication. Searches of PubMed and Medline are recommended. It is also recommended to look for comments on PubPeer. These are readily accessed by downloading the PubPeer plugin (https://www.pubpeer.com/static/extensions), which will automatically flag a study with comments if you are examining it. The presence of critical correspondence or PubPeer comments should not automatically trigger concerns however, because some critiques of this nature may lack merit, or may not relate to trustworthiness of the study. We recommend that these comments should be carefully considered, as they might assist the reviewer in completing their assessment using the INSPECT-SR tool (for example, by directing attention to a problematic feature that can then be incorporated into the corresponding domain-level judgement).

• Further guidance for searching for post-publication amendments, including expressions of concern, is included in the Cochrane Handbook for Systematic Reviews of Interventions (13) and its associated technical supplement (https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-04-technical-supplement-searching-and-selecting-studies). You may wish to consult with an Information Specialist if further assistance is needed.

• The answer to this check should contribute to a domain-level judgement.`,
    example: `1. While assessing a clinical trial of a probiotic supplement for gestational diabetes, a reviewer searches for the study on https://retractiondatabase.org/ by searching on the study DOI. The index study is included in the search results, indicating that it has an associated post-publication notice, labelled as "Concerns/ Issues About data". Navigating to the article on the journal website reveals an "Editor's Note" reporting that the article is being investigated due to integrity concerns. The reviewer answers "yes" for this check, and this response contributes to the domain-level judgement.

2. While assessing a clinical trial of a weight-loss drug, the reviewer identifies a critical comment on PubPeer. On reviewing the comment, the reviewer learns that the criticism relates to the dose of drug used in the study. Because this is not relevant to the assessment of the study's trustworthiness, and because no other post-publication notices relating to the study were identified, the reviewer answers "no" for this check, and this response contributes to the domain-level judgement.`,
  },

  "postPublication-2": {
    title: getCheckTitle(0, 2), // Check 1.3
    guidelines: `• We suggest the reviewer searches the first, corresponding, and last author (at minimum) on the Retraction Watch database http://retractiondatabase.org/

• It can be helpful to repeat the search with first names and last names switched, because journals and publishers may transpose names.

• A track record of problems relating to trustworthiness may introduce doubts about the index study.

• The reviewer should pay close attention to the content of any notices associated with the author. For example, a previous retraction due to an honest error may not warrant any concerns based on the author's track record.

• If the reviewer does perform these searches in relation to middle authors, the reviewer should consider whether a track record of integrity problems relating to middle authors on the index study are sufficient to introduce concerns about the trustworthiness of the index study. The reviewer should consider the contribution statement in the manuscript to assist with this decision.

• If comments relating to integrity issues on other studies from the author team are identified in other locations, not originating from the journal or publisher (for example, in a letter to the editor or PubPeer) we suggest that the reviewer considers the content of the comment as it may be useful in helping to identify problematic features of the index study.

• The answer to this check should contribute to a domain-level judgement.`,
    example: `1. A reviewer performs this check on a trial of a probiotic supplement for gestational diabetes by searching for the first and last author on http://retractiondatabase.org/. The search on the last author returns a large number of notices, including numerous retractions and expressions of concern relating to concerns over data integrity. The reviewer reads some of the associated notices to ensure that they are related to data integrity concerns. The reviewer answers "yes" for this check, and this response contributes to the domain-level judgement.

2. A reviewer performs this check on a trial of a dietary intervention for sleep apnea, by searching for the first and last author on http://retractiondatabase.org/. This identifies a publication describing a similar trial conducted concurrently by the author team that has been retracted. The retraction alludes to a lack of transparency on behalf of the authors but is not entirely clear about the motivation for the retraction. The reviewer answers "yes" for this check, and this response contributes to the domain-level judgement.`,
  },

  // Conduct and Transparency (2.2)
  "conduct-1": {
    title: getCheckTitle(1, 1), // Check 2.2
    guidelines: `• Absent or retrospective registration makes it difficult to determine whether the reported methods and results are an accurate reflection of a planned programme of work.

• This check speaks of concerns relating to the timing of study registration rather than to the absence of "prospective" (as opposed to "retrospective") registration. If registration occurs shortly after the commencement of participant recruitment (i.e. when only a small proportion of the target sample size has been recruited) it might not be strictly "prospective", but might not warrant concerns, for example. The implications of the timing of the registration should be considered in relation to the particular details of the index study.

• Be aware that study registration only became more established in recent years, and regulations and expectations can differ internationally.

• The answer to this check should contribute to a domain-level judgement.`,
    example: `A clinical trial is registered on ClinicalTrials.gov with a registration number NCTXXXXXXXXX provided in the manuscript. Clicking on the Record History section of the record, we see that Version 1, the earliest version of the registration, was submitted on 6th July 2010. The trial manuscript states that participants were recruited between August 2008 and April 2010. Accordingly, this trial was retrospectively registered. As a result, it is impossible to know whether key features of the trial, such as sample size, outcomes, and eligibility criteria, were prospectively determined. The reviewer answers "yes" for this check, and this response contributes to the domain-level judgement.`,
  },
};

// Helper function to get help content for a specific check
export const getCheckHelp = (domainKey: string, checkIndex: number): CheckHelpContent | null => {
  const key = `${domainKey}-${checkIndex}`;
  return checkHelpContent[key] || null;
};

// Helper function to generate check title dynamically
export const generateCheckTitle = (domainKey: string, checkIndex: number): string => {
  const domainIndices: { [key: string]: number } = {
    postPublication: 0,
    conduct: 1,
    textFigures: 2,
    results: 3,
  };

  const domainIndex = domainIndices[domainKey] ?? 0;
  return getCheckTitle(domainIndex, checkIndex);
};
