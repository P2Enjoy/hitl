export class HitlError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "HitlError";
  }
}

export class HitlDenied extends HitlError {
  constructor(message: string) {
    super(message);
    this.name = "HitlDenied";
  }
}

export class HitlTimeout extends HitlError {
  constructor(message: string) {
    super(message);
    this.name = "HitlTimeout";
  }
}

export class HitlVerificationError extends HitlError {
  constructor(message: string) {
    super(message);
    this.name = "HitlVerificationError";
  }
}

export class HitlExtensionUnavailable extends HitlError {
  constructor(message: string) {
    super(message);
    this.name = "HitlExtensionUnavailable";
  }
}
