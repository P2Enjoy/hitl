export class HitlExtensionError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "HitlExtensionError";
  }
}

export class KeypairNotFoundError extends HitlExtensionError {
  constructor() {
    super("No keypair found in session storage. Please log in first.");
    this.name = "KeypairNotFoundError";
  }
}

export class NotAuthenticatedError extends HitlExtensionError {
  constructor() {
    super("Not authenticated with the OAuth server. Please log in first.");
    this.name = "NotAuthenticatedError";
  }
}

export class ChallengeDeniedError extends HitlExtensionError {
  constructor() {
    super("User denied the challenge.");
    this.name = "ChallengeDeniedError";
  }
}

export class ChallengeExpiredError extends HitlExtensionError {
  constructor() {
    super("Challenge has expired.");
    this.name = "ChallengeExpiredError";
  }
}
