# Biometric Privacy & Security Policy

This system has been designed in strict accordance with biometric privacy principles (e.g. GDPR Article 9, FERPA for educational institutions).

## 1. Principles of Authorized Classroom Use

1. **Explicit Consent & Purpose Limitation**
   - The system is built exclusively for authorized classroom attendance and verified student identification.
   - Unauthorized surveillance, clandestine recording, and public tracking are strictly prohibited.

2. **Decoupled Data Architecture**
   - Biometric vectors (512-dimensional numerical embeddings) are stored separately from personally identifiable information (PII).
   - Raw facial camera streams are processed in memory and discarded immediately; raw video frames are **never stored permanently** on disk.

3. **Configurable Biometric Retention Policies**
   - Face samples captured during enrollment are stored in a restricted local folder (`data/faces/`).
   - Administrators can configure image retention windows or opt to store only mathematical embeddings without keeping image files.

4. **Right to Erasure (Complete Data Deletion)**
   - Deleting a student via `DELETE /persons/{id}` performs an atomic triple-purge:
     1. Deletes database records from PostgreSQL/SQLite.
     2. Deletes physical face crop image files from storage.
     3. Removes all 512-D vectors from the FAISS index and rebuilds the vector index in real time.

5. **Access Control & Network Security**
   - Administrative endpoints are protected via JWT bearer tokens and password hashing with salted bcrypt.
   - CORS is restricted to trusted dashboard origins.
   - Path traversal protections prevent arbitrary file system access.
