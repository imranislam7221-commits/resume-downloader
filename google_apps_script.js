/**
 * ==============================================================================
 * ⚡ Real-Time Autonomous Resume Downloader (Google Cloud / Google Apps Script)
 * ==============================================================================
 * 
 * কাজ:
 * ১. জিমেইলে আসা নতুন রেজ্যুমে (.pdf, .docx, .doc) স্বয়ংক্রিয়ভাবে ডিটেক্ট করবে।
 * ২. ইমেইল ফ্ল্যাগ হওয়ার আগেই কয়েক সেকেন্ডের মধ্যে Google Drive-এ সেভ করে রাখবে।
 * ৩. প্রতিবার প্রসেস শেষে ইমেলকে 'Resume_Processed' লেবেল দেবে যাতে ডুপ্লিকেট না হয়।
 * ৪. আপনার পিসিতে Google Drive for Desktop থাকলে ফাইল সাথে সাথে লোকালে ডাউনলোড হয়ে যাবে।
 */

// কনফিগারেশন
const FOLDER_NAME = "Resumes_Downloaded";         // যে গুগল ড্রাইভ ফোল্ডারে ফাইল সেভ হবে
const PROCESSED_LABEL = "Resume_Processed";       // প্রসেস হওয়া ইমেইলের জন্য জিমেইল লেবেল
const ALLOWED_EXTENSIONS = [".pdf", ".docx", ".doc"]; // রেজ্যুমে এক্সটেনশন

function autoDownloadResumes() {
  try {
    // ১. গুগল ড্রাইভে ফোল্ডার আছে কি না চেক করা, না থাকলে অটো তৈরি করা
    let folder;
    const folders = DriveApp.getFoldersByName(FOLDER_NAME);
    if (folders.hasNext()) {
      folder = folders.next();
    } else {
      folder = DriveApp.createFolder(FOLDER_NAME);
    }

    // ২. জিমেইলে লেবেল চেক করা, না থাকলে তৈরি করা
    let label = GmailApp.getUserLabelByName(PROCESSED_LABEL);
    if (!label) {
      label = GmailApp.createLabel(PROCESSED_LABEL);
    }

    // ৩. আনরিড ইমেইল খোঁজা যেগুলোতে এটাচমেন্ট আছে এবং এখনও প্রসেস করা হয়নি
    const query = 'has:attachment -label:' + PROCESSED_LABEL + ' is:unread';
    const threads = GmailApp.search(query, 0, 30); // একসাথে ৩০টি ইমেইল পর্যন্ত চেক করবে

    if (threads.length === 0) {
      return; // নতুন কোনো ইমেইল না থাকলে শেষ
    }

    for (let i = 0; i < threads.length; i++) {
      const thread = threads[i];
      const messages = thread.getMessages();

      for (let j = 0; j < messages.length; j++) {
        const msg = messages[j];
        if (msg.isUnread()) {
          const attachments = msg.getAttachments();
          const sender = msg.getFrom();
          const date = msg.getDate();
          
          // টাইমস্ট্যাম্প ফরম্যাট (e.g., 20261017_1030)
          const timeStr = Utilities.formatDate(date, Session.getScriptTimeZone(), "yyyyMMdd_HHmm");

          // সেন্ডারের পরিষ্কার নাম বের করা
          let cleanSender = sender.replace(/<.*?>/, "").trim().replace(/[^a-zA-Z0-9_\- ]/g, "");
          if (!cleanSender) cleanSender = "Candidate";

          for (let k = 0; k < attachments.length; k++) {
            const att = attachments[k];
            const originalName = att.getName();
            const lowerName = originalName.toLowerCase();

            // এক্সটেনশন চেক
            const isMatch = ALLOWED_EXTENSIONS.some(ext => lowerName.endsWith(ext));
            if (isMatch) {
              const uniqueFileName = timeStr + "_" + cleanSender + "_" + originalName;
              
              // গুগল ড্রাইভে সেভ করা
              folder.createFile(att.copyBlob().setName(uniqueFileName));
            }
          }
        }
      }

      // ইমেইলটি প্রসেসড লেবেল দিয়ে মার্ক রিড করা
      thread.addLabel(label);
      thread.markRead();
    }
  } catch (error) {
    Logger.log("Error during resume download: " + error.toString());
  }
}
