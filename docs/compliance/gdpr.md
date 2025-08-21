# GDPR Compliance Framework

## General Data Protection Regulation (GDPR) Implementation

### Legal Requirements

**Scope:** EU residents and EU data processing  
**Effective Date:** May 25, 2018  
**Jurisdiction:** European Union + EEA + UK (GDPR-based)

### Lawful Basis for Processing

#### Article 6 Lawful Bases

```typescript
enum LawfulBasis {
  CONSENT = "consent", // Freely given, specific, informed, unambiguous
  CONTRACT = "contract", // Necessary for contract performance
  LEGAL_OBLIGATION = "legal-obligation", // Compliance with legal requirement
  VITAL_INTERESTS = "vital-interests", // Protect life or physical safety
  PUBLIC_TASK = "public-task", // Performance of public interest task
  LEGITIMATE_INTERESTS = "legitimate-interests", // Balancing test required
}

interface ProcessingActivity {
  activityId: string;
  purpose: string;
  lawfulBasis: LawfulBasis;
  dataCategories: string[];
  dataSubjects: string[];
  recipients: string[];
  retentionPeriod: string;
  internationalTransfers: boolean;
  safeguards?: string[];
}
```

#### Educational Context Lawful Bases

- **Student Registration:** Contract (Article 6(1)(b))
- **Learning Analytics:** Legitimate Interests (Article 6(1)(f))
- **Marketing Communications:** Consent (Article 6(1)(a))
- **Legal Reporting:** Legal Obligation (Article 6(1)(c))
- **Child Safety:** Vital Interests (Article 6(1)(d))

### Special Category Data (Article 9)

#### Additional Lawful Basis Required

```typescript
enum SpecialCategoryBasis {
  EXPLICIT_CONSENT = "explicit-consent",
  EMPLOYMENT_SOCIAL_SECURITY = "employment",
  VITAL_INTERESTS = "vital-interests",
  PUBLIC_INTEREST = "public-interest",
  MEDICAL_DIAGNOSIS = "medical",
  ARCHIVING_RESEARCH = "archiving-research",
}

interface SpecialCategoryProcessing {
  dataType:
    | "health"
    | "biometric"
    | "genetic"
    | "religious"
    | "political"
    | "ethnic";
  lawfulBasis: LawfulBasis; // Article 6 basis
  specialCategoryBasis: SpecialCategoryBasis; // Article 9 basis
  additionalSafeguards: string[];
  dataMinimization: boolean;
  purposeLimitation: boolean;
}
```

#### Educational Special Categories

- **Health Data:** Medical accommodations, disability support
- **Biometric Data:** Fingerprint login, facial recognition
- **Religious Data:** Dietary requirements, holiday observances
- **Political Data:** Student government, political science coursework

### Data Subject Rights Implementation

#### Right of Access (Article 15)

```typescript
export class GDPRAccessRequestProcessor {
  async processAccessRequest(
    dataSubjectId: string,
    requestDetails: AccessRequest,
  ): Promise<AccessResponse> {
    // Must respond within 1 month (extendable by 2 months if complex)
    const responseDeadline = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000);

    // Verify data subject identity
    await this.verifyIdentity(dataSubjectId, requestDetails.identityProof);

    // Compile personal data
    const personalData = await this.compilePersonalData(dataSubjectId);

    // Generate response with required information
    return {
      personalDataCopy: personalData,
      processingPurposes: await this.getProcessingPurposes(dataSubjectId),
      categoriesOfData: this.categorizePersonalData(personalData),
      recipients: await this.getDataRecipients(dataSubjectId),
      retentionPeriods: await this.getRetentionPeriods(dataSubjectId),
      dataSubjectRights: this.getDataSubjectRightsInfo(),
      complaintRights: this.getComplaintRightsInfo(),
      dataSource: await this.getDataSources(dataSubjectId),
      automatedDecisionMaking: await this.getAutomatedDecisions(dataSubjectId),
      responseDate: new Date(),
      responseDeadline,
    };
  }

  private async compilePersonalData(
    dataSubjectId: string,
  ): Promise<PersonalDataExport> {
    // Must provide data in structured, commonly used, machine-readable format
    return {
      format: "JSON",
      encoding: "UTF-8",
      profileData: await this.getProfileData(dataSubjectId),
      educationalRecords: await this.getEducationalData(dataSubjectId),
      communicationHistory: await this.getCommunicationHistory(dataSubjectId),
      systemLogs: await this.getRelevantSystemLogs(dataSubjectId),
      aiInteractions: await this.getAIInteractionHistory(dataSubjectId),
      consentHistory: await this.getConsentHistory(dataSubjectId),
    };
  }
}
```

#### Right to Rectification (Article 16)

```typescript
export class GDPRRectificationProcessor {
  async processRectificationRequest(
    dataSubjectId: string,
    rectificationRequest: RectificationRequest,
  ): Promise<RectificationResponse> {
    // Verify accuracy claims
    const accuracyReview = await this.reviewAccuracyClaims(
      rectificationRequest.claimedInaccuracies,
    );

    if (accuracyReview.hasInaccuracies) {
      // Rectify inaccurate data
      await this.rectifyPersonalData(
        dataSubjectId,
        accuracyReview.correctionsNeeded,
      );

      // Notify recipients if data was disclosed
      const recipients = await this.getDataRecipients(dataSubjectId);
      await this.notifyRecipientsOfRectification(
        recipients,
        accuracyReview.correctionsNeeded,
      );

      return {
        status: "completed",
        correctionsApplied: accuracyReview.correctionsNeeded,
        recipientsNotified: recipients.length,
        completionDate: new Date(),
      };
    }

    // Complete incomplete data
    if (rectificationRequest.completionRequested) {
      await this.completeIncompleteData(
        dataSubjectId,
        rectificationRequest.additionalData,
      );
    }

    return {
      status: "completed",
      completionApplied: rectificationRequest.additionalData ? true : false,
      completionDate: new Date(),
    };
  }
}
```

#### Right to Erasure (Article 17)

```typescript
export class GDPRErasureProcessor {
  async processErasureRequest(
    dataSubjectId: string,
    erasureRequest: ErasureRequest,
  ): Promise<ErasureResponse> {
    // Check if erasure grounds apply
    const erasureGrounds = await this.checkErasureGrounds(
      dataSubjectId,
      erasureRequest.grounds,
    );

    if (!erasureGrounds.valid) {
      return {
        status: "rejected",
        rejectionReason: erasureGrounds.reason,
        rightToComplain: this.getComplaintInfo(),
      };
    }

    // Check for overriding legitimate interests
    const overridingInterests = await this.checkOverridingInterests(
      dataSubjectId,
      erasureRequest.scope,
    );

    if (overridingInterests.exist) {
      return {
        status: "restricted",
        restrictionReason: "overriding-legitimate-interests",
        dataRestricted: true,
        processingLimited: overridingInterests.allowedProcessing,
      };
    }

    // Perform erasure
    const erasureResult = await this.erasePersonalData(
      dataSubjectId,
      erasureRequest.scope,
    );

    // Notify recipients and search engines if data was made public
    await this.notifyRecipientsOfErasure(erasureResult.recipientsToNotify);

    if (erasureResult.wasPublic) {
      await this.requestSearchEngineRemoval(erasureResult.publicUrls);
    }

    return {
      status: "completed",
      dataErased: erasureResult.categoriesErased,
      backupsErased: erasureResult.backupsErased,
      recipientsNotified: erasureResult.recipientsToNotify.length,
      erasureDate: new Date(),
    };
  }

  private async checkErasureGrounds(
    dataSubjectId: string,
    grounds: ErasureGrounds,
  ): Promise<ErasureValidation> {
    const validGrounds = [
      "no-longer-necessary", // Purpose fulfilled
      "consent-withdrawn", // Consent was the basis
      "unlawful-processing", // Processing was unlawful
      "legal-obligation", // Erasure required by law
      "child-consent", // Consent given as child
      "direct-marketing-objection", // Objection to marketing
    ];

    // Educational context special considerations
    if (grounds === "no-longer-necessary") {
      const stillEnrolled = await this.checkActiveEnrollment(dataSubjectId);
      if (stillEnrolled) {
        return {
          valid: false,
          reason: "Still necessary for educational service provision",
        };
      }
    }

    return { valid: validGrounds.includes(grounds) };
  }
}
```

#### Right to Data Portability (Article 20)

```typescript
export class GDPRPortabilityProcessor {
  async processPortabilityRequest(
    dataSubjectId: string,
    portabilityRequest: PortabilityRequest,
  ): Promise<PortabilityResponse> {
    // Check if portability applies (consent or contract basis only)
    const basisCheck = await this.checkLawfulBasisForPortability(dataSubjectId);

    if (!basisCheck.portable) {
      return {
        status: "not-applicable",
        reason: "Data not processed on basis of consent or contract",
      };
    }

    // Extract portable data (provided by data subject)
    const portableData = await this.extractPortableData(
      dataSubjectId,
      portabilityRequest.dataCategories,
    );

    // Format in structured, machine-readable format
    const formattedData = this.formatForPortability(
      portableData,
      portabilityRequest.preferredFormat,
    );

    if (
      portabilityRequest.directTransfer &&
      portabilityRequest.targetController
    ) {
      // Direct transmission to another controller
      const transferResult = await this.directDataTransfer(
        formattedData,
        portabilityRequest.targetController,
      );

      return {
        status: "transferred",
        targetController: portabilityRequest.targetController,
        transferDate: new Date(),
        dataCategories: portabilityRequest.dataCategories,
      };
    } else {
      // Provide to data subject
      return {
        status: "provided",
        dataPackage: formattedData,
        format: portabilityRequest.preferredFormat,
        provisionDate: new Date(),
      };
    }
  }

  private async extractPortableData(
    dataSubjectId: string,
    categories: string[],
  ): Promise<PortableDataSet> {
    // Only data provided by data subject is portable
    return {
      profileInformation: await this.getUserProvidedProfile(dataSubjectId),
      userContent: await this.getUserGeneratedContent(dataSubjectId),
      preferences: await this.getUserPreferences(dataSubjectId),
      // Exclude: inferred data, derived data, organizational data
      metadata: {
        extractionDate: new Date(),
        dataSubjectId: dataSubjectId,
        portabilityBasis: "consent-or-contract",
      },
    };
  }
}
```

### Consent Management

#### GDPR-Compliant Consent

```typescript
interface GDPRConsent {
  consentId: string;
  dataSubjectId: string;
  consentDate: Date;
  consentVersion: string;
  processingPurposes: string[];
  dataCategories: string[];
  recipients: string[];
  retentionPeriod: string;
  withdrawalMechanism: string;
  consentEvidence: string; // How consent was captured
  freelyGiven: boolean;
  specific: boolean;
  informed: boolean;
  unambiguous: boolean;
}

export class GDPRConsentManager {
  async captureConsent(consentRequest: ConsentRequest): Promise<ConsentResult> {
    // Validate consent meets GDPR requirements
    this.validateGDPRConsent(consentRequest);

    // Present clear, plain language consent form
    const consentForm = await this.generateConsentForm({
      purposes: consentRequest.purposes,
      dataTypes: consentRequest.dataCategories,
      recipients: consentRequest.recipients,
      retentionPeriod: consentRequest.retentionPeriod,
      withdrawalInstructions: this.getWithdrawalInstructions(),
    });

    // Capture consent with evidence
    const consent = await this.recordConsent({
      ...consentRequest,
      consentEvidence: consentForm.interactionLog,
      timestamp: new Date(),
      consentMethod: "explicit-opt-in",
    });

    return {
      consentId: consent.id,
      validUntil: this.calculateConsentExpiry(consent),
      withdrawalUrl: this.generateWithdrawalUrl(consent.id),
    };
  }

  private validateGDPRConsent(request: ConsentRequest): void {
    // Freely given - no detriment for refusal
    if (request.requiredForService && !request.legitimateInterestAlternative) {
      throw new Error(
        "Consent not freely given - service conditional on consent",
      );
    }

    // Specific - clear purpose identification
    if (
      !request.purposes.length ||
      request.purposes.includes("general-processing")
    ) {
      throw new Error("Consent must be specific to processing purposes");
    }

    // Informed - all material information provided
    if (!request.dataCategories.length || !request.recipients.length) {
      throw new Error("Consent must be informed with complete disclosure");
    }

    // Unambiguous - clear affirmative action required
    if (
      request.consentMechanism === "pre-ticked-box" ||
      request.consentMechanism === "inactivity"
    ) {
      throw new Error("Consent must be unambiguous positive action");
    }
  }

  async withdrawConsent(
    consentId: string,
    withdrawalRequest: WithdrawalRequest,
  ): Promise<WithdrawalResult> {
    // Consent withdrawal must be as easy as giving consent
    const consent = await this.getConsent(consentId);

    // Stop processing based on withdrawn consent
    await this.stopConsentBasedProcessing(consent);

    // Record withdrawal
    const withdrawal = await this.recordWithdrawal({
      consentId,
      withdrawalDate: new Date(),
      withdrawalMethod: withdrawalRequest.method,
      dataSubjectId: consent.dataSubjectId,
    });

    // Notify data subject of withdrawal processing
    return {
      withdrawalId: withdrawal.id,
      processingStoppedDate: new Date(),
      dataRetainedForLegitimateInterests: await this.checkRetainedData(consent),
      alternativeLawfulBasis: await this.checkAlternativeBasis(consent),
    };
  }
}
```

### Data Protection Impact Assessment (DPIA)

#### DPIA Trigger Conditions

```typescript
interface DPIAAssessment {
  triggerConditions: {
    systematicEvaluation: boolean; // Automated profiling
    largScaleSpecialCategory: boolean; // Large scale special category data
    systematicMonitoring: boolean; // Public area monitoring
    vulnerableDataSubjects: boolean; // Children, employees
    innovativeTechnology: boolean; // New technology use
    preventDataSubjectRights: boolean; // Blocks data subject rights
    matchingCombiningData: boolean; // Data from multiple sources
    riskToRightsFreedoms: boolean; // High risk assessment
  };
  requiresDPIA: boolean;
  dpiaCompleted: boolean;
  consultationRequired: boolean;
}

export class DPIAProcessor {
  async assessDPIARequirement(
    processingActivity: ProcessingActivity,
  ): Promise<DPIAAssessment> {
    const triggers = {
      systematicEvaluation: this.checkSystematicEvaluation(processingActivity),
      largScaleSpecialCategory:
        this.checkLargeScaleSpecialCategory(processingActivity),
      systematicMonitoring: this.checkSystematicMonitoring(processingActivity),
      vulnerableDataSubjects: this.checkVulnerableSubjects(processingActivity),
      innovativeTechnology: this.checkInnovativeTechnology(processingActivity),
      preventDataSubjectRights: this.checkRightsPrevention(processingActivity),
      matchingCombiningData: this.checkDataMatching(processingActivity),
      riskToRightsFreedoms: this.checkHighRisk(processingActivity),
    };

    const requiresDPIA = Object.values(triggers).some((trigger) => trigger);

    return {
      triggerConditions: triggers,
      requiresDPIA,
      dpiaCompleted: requiresDPIA
        ? await this.checkDPIACompleted(processingActivity.id)
        : false,
      consultationRequired: requiresDPIA
        ? await this.checkConsultationRequired(processingActivity)
        : false,
    };
  }

  private checkSystematicEvaluation(activity: ProcessingActivity): boolean {
    // AI-based educational recommendations, automated grading
    const aiActivities = [
      "automated-assessment",
      "learning-analytics",
      "predictive-modeling",
      "behavioral-profiling",
    ];

    return aiActivities.some((aiActivity) =>
      activity.purpose.toLowerCase().includes(aiActivity),
    );
  }

  private checkVulnerableSubjects(activity: ProcessingActivity): boolean {
    // Students are considered vulnerable due to power imbalance
    return (
      activity.dataSubjects.includes("students") ||
      activity.dataSubjects.includes("minors")
    );
  }
}
```

### International Data Transfers

#### Transfer Mechanisms

```typescript
enum TransferMechanism {
  ADEQUACY_DECISION = "adequacy-decision",
  STANDARD_CONTRACTUAL_CLAUSES = "standard-contractual-clauses",
  BINDING_CORPORATE_RULES = "binding-corporate-rules",
  CERTIFICATION = "certification",
  CODE_OF_CONDUCT = "code-of-conduct",
  DEROGATIONS = "derogations",
}

interface InternationalTransfer {
  transferId: string;
  dataExported: string[];
  destinationCountry: string;
  recipient: string;
  transferMechanism: TransferMechanism;
  safeguards: string[];
  dataSubjectRights: string[];
  enforceableRights: boolean;
  effectiveRemedies: boolean;
}

export class InternationalTransferManager {
  async validateTransfer(
    transferRequest: TransferRequest,
  ): Promise<TransferValidation> {
    // Check adequacy decision first
    const adequacyStatus = await this.checkAdequacyDecision(
      transferRequest.destinationCountry,
    );

    if (adequacyStatus.adequate) {
      return {
        approved: true,
        mechanism: TransferMechanism.ADEQUACY_DECISION,
        additionalSafeguards: [],
      };
    }

    // Check for appropriate safeguards
    const safeguards = await this.validateSafeguards(transferRequest);

    if (!safeguards.sufficient) {
      throw new Error(
        `Insufficient safeguards for transfer to ${transferRequest.destinationCountry}`,
      );
    }

    return {
      approved: true,
      mechanism: safeguards.mechanism,
      additionalSafeguards: safeguards.measures,
    };
  }

  async implementSCCs(
    transferAgreement: TransferAgreement,
  ): Promise<SCCImplementation> {
    // Use EU Standard Contractual Clauses
    const sccTemplate = await this.getSCCTemplate("eu-2021");

    // Complete annexes with transfer details
    const completedSCCs = {
      ...sccTemplate,
      annexI: {
        dataExporter: transferAgreement.dataExporter,
        dataImporter: transferAgreement.dataImporter,
        dataSubjects: transferAgreement.dataSubjects,
        dataCategories: transferAgreement.dataCategories,
        recipients: transferAgreement.recipients,
        retentionPeriod: transferAgreement.retentionPeriod,
      },
      annexII: {
        technicalSafeguards: transferAgreement.technicalMeasures,
        organizationalSafeguards: transferAgreement.organizationalMeasures,
      },
      annexIII: {
        competentSupervisionAuthority: "relevant-dpa",
      },
    };

    return {
      sccId: generateId(),
      sccVersion: "eu-2021",
      signedDate: new Date(),
      effectiveDate: transferAgreement.effectiveDate,
      documentUrl: await this.storeSCCs(completedSCCs),
    };
  }
}
```

### Breach Notification

#### GDPR Breach Response

```typescript
interface PersonalDataBreach {
  breachId: string;
  discoveryDate: Date;
  breachDate: Date;
  dataCategories: string[];
  dataSubjectsAffected: number;
  riskLevel: "low" | "high";
  riskFactors: string[];
  containmentMeasures: string[];
  recurrencePrevention: string[];
  dpaNotificationRequired: boolean;
  dataSubjectNotificationRequired: boolean;
}

export class GDPRBreachProcessor {
  async processDataBreach(
    breachDetails: BreachDetails,
  ): Promise<BreachResponse> {
    // Must notify DPA within 72 hours of becoming aware
    const dpaDeadline = new Date(
      breachDetails.discoveryDate.getTime() + 72 * 60 * 60 * 1000,
    );

    // Assess risk to rights and freedoms
    const riskAssessment = await this.assessBreachRisk(breachDetails);

    // Notify supervisory authority if likely to result in risk
    if (riskAssessment.riskLevel !== "unlikely") {
      await this.notifyDPA({
        breachId: breachDetails.breachId,
        notificationDeadline: dpaDeadline,
        riskAssessment,
        containmentMeasures: breachDetails.containmentMeasures,
      });
    }

    // Notify data subjects if high risk
    if (riskAssessment.riskLevel === "high") {
      await this.notifyDataSubjects({
        breachId: breachDetails.breachId,
        affectedSubjects: breachDetails.affectedDataSubjects,
        mitigationAdvice: riskAssessment.mitigationAdvice,
      });
    }

    // Document breach for regulatory compliance
    await this.documentBreach({
      ...breachDetails,
      riskAssessment,
      notificationActions: {
        dpaNotified: riskAssessment.riskLevel !== "unlikely",
        dataSubjectsNotified: riskAssessment.riskLevel === "high",
      },
    });

    return {
      breachId: breachDetails.breachId,
      dpaNotificationSent: riskAssessment.riskLevel !== "unlikely",
      dataSubjectNotificationSent: riskAssessment.riskLevel === "high",
      nextSteps: riskAssessment.recommendedActions,
    };
  }
}
```
