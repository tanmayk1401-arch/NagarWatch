/**
 * ==========================================================================
 * NagarWatch - Civic Issue Reporting Platform
 * File: static/js/mock_data.js
 * Purpose: Centralized demonstration dataset for reports, categories, and metrics.
 * Note: Clearly labelled as demonstration data for frontend-only development.
 * ==========================================================================
 */

const NAGARWATCH_MOCK_REPORTS = [
  {
    id: 101,
    title: "Large Dangerous Pothole near MG Road Flyover",
    description: "Deep pothole causing traffic congestion and severe risk to two-wheelers during peak evening hours. Rainwater has accumulated inside it.",
    category: "Roads & Footpaths",
    location: "MG Road, North Lane, Ward 4",
    latitude: 12.9716,
    longitude: 77.5946,
    status: "pending",
    status_display: "Pending Review",
    priority: "urgent",
    created_at: "2 hours ago",
    reported_by: "Rahul M.",
    confirmations_count: 24,
    disputes_count: 1,
    image_svg_type: "pothole",
    timeline: [
      { step: "Submitted", date: "Today, 10:15 AM", done: true, current: false },
      { step: "Verification", date: "Pending Field Review", done: false, current: true },
      { step: "In Progress", date: "Work Order Pending", done: false, current: false },
      { step: "Resolved", date: "Expected in 48 hours", done: false, current: false }
    ],
    ai_suggestions: {
      suggested_category: "Roads & Footpaths (98% confidence)",
      suggested_severity: "High / Urgent (Risk of vehicle damage)",
      duplicate_flag: "No direct duplicates detected in 500m radius"
    }
  },
  {
    id: 102,
    title: "Broken Streetlight causing safety hazard at night",
    description: "Main pole #ST-44 has been non-functional for the past 4 days. The entire alley behind the public market is pitch dark at night.",
    category: "Streetlights",
    location: "Sector 4, Main Market Lane",
    latitude: 12.9780,
    longitude: 77.6010,
    status: "verified",
    status_display: "Verified",
    priority: "medium",
    created_at: "Yesterday",
    reported_by: "Priya S.",
    confirmations_count: 15,
    disputes_count: 0,
    image_svg_type: "light",
    timeline: [
      { step: "Submitted", date: "Yesterday, 04:30 PM", done: true, current: false },
      { step: "Verification", date: "Verified by Ward Inspector", done: true, current: false },
      { step: "In Progress", date: "Technician Dispatched", done: false, current: true },
      { step: "Resolved", date: "Pending Bulb Replacement", done: false, current: false }
    ],
    ai_suggestions: {
      suggested_category: "Streetlights (95% confidence)",
      suggested_severity: "Medium Priority",
      duplicate_flag: "Similar report #98 verified yesterday in Sector 4"
    }
  },
  {
    id: 103,
    title: "Major Drinking Water Pipeline Leakage",
    description: "Treated clean drinking water has been gushing onto the sidewalk near the hospital entrance. Thousands of liters wasted daily.",
    category: "Water & Drainage",
    location: "Near City General Hospital, Sector 2",
    latitude: 12.9650,
    longitude: 77.5890,
    status: "in-progress",
    status_display: "In Progress",
    priority: "high",
    created_at: "3 days ago",
    reported_by: "Dr. Ananya V.",
    confirmations_count: 42,
    disputes_count: 2,
    image_svg_type: "water",
    timeline: [
      { step: "Submitted", date: "3 days ago", done: true, current: false },
      { step: "Verification", date: "Verified by Water Board", done: true, current: false },
      { step: "In Progress", date: "Excavation and Valve Repair", done: true, current: true },
      { step: "Resolved", date: "Target: Today evening", done: false, current: false }
    ],
    ai_suggestions: {
      suggested_category: "Water & Drainage (99% confidence)",
      suggested_severity: "High Priority (Resource wastage & flooding)",
      duplicate_flag: "2 community reports linked together"
    }
  },
  {
    id: 104,
    title: "Illegal Garbage Accumulation near Community Park",
    description: "Commercial plastic and vegetable waste being dumped openly beside the children's playground. Foul smell and stray animal menace.",
    category: "Garbage & Waste",
    location: "Green Glen Park Gate #2, Ward 12",
    latitude: 12.9825,
    longitude: 77.6150,
    status: "resolved",
    status_display: "Resolved",
    priority: "low",
    created_at: "5 days ago",
    reported_by: "Karthik R.",
    confirmations_count: 31,
    disputes_count: 0,
    image_svg_type: "waste",
    timeline: [
      { step: "Submitted", date: "5 days ago", done: true, current: false },
      { step: "Verification", date: "Verified by Sanitary Staff", done: true, current: false },
      { step: "In Progress", date: "Cleanup Crew Dispatched", done: true, current: false },
      { step: "Resolved", date: "Waste cleared & bin installed", done: true, current: true }
    ],
    ai_suggestions: {
      suggested_category: "Garbage & Waste (96% confidence)",
      suggested_severity: "Normal / Moderate Priority",
      duplicate_flag: "Resolved"
    }
  },
  {
    id: 105,
    title: "Broken Footpath Paver Blocks & Exposed Drain",
    description: "Pedestrian walkway paver blocks have collapsed creating an open drainage hazard for elderly residents and school students.",
    category: "Roads & Footpaths",
    location: "14th Cross, Malleshwaram",
    latitude: 12.9910,
    longitude: 77.5710,
    status: "verified",
    status_display: "Verified",
    priority: "high",
    created_at: "4 days ago",
    reported_by: "Sunita M.",
    confirmations_count: 19,
    disputes_count: 1,
    image_svg_type: "footpath",
    timeline: [
      { step: "Submitted", date: "4 days ago", done: true, current: false },
      { step: "Verification", date: "Field Inspection Completed", done: true, current: false },
      { step: "In Progress", date: "Material Order Placed", done: false, current: true },
      { step: "Resolved", date: "Pending Installation", done: false, current: false }
    ],
    ai_suggestions: {
      suggested_category: "Roads & Footpaths (94% confidence)",
      suggested_severity: "High Priority (Pedestrian hazard)",
      duplicate_flag: "No duplicates found"
    }
  },
  {
    id: 106,
    title: "Dead Streetlight on High Traffic Junction",
    description: "Signal junction lights are dark creating severe collision risk for turning vehicles between 8 PM and 11 PM.",
    category: "Streetlights",
    location: "Ring Road Circle, Ward 8",
    latitude: 12.9550,
    longitude: 77.6200,
    status: "pending",
    status_display: "Pending Review",
    priority: "urgent",
    created_at: "Just now",
    reported_by: "Vikram N.",
    confirmations_count: 8,
    disputes_count: 0,
    image_svg_type: "light",
    timeline: [
      { step: "Submitted", date: "Today, 01:20 PM", done: true, current: false },
      { step: "Verification", date: "Queued for Inspection", done: false, current: true },
      { step: "In Progress", date: "Pending", done: false, current: false },
      { step: "Resolved", date: "Pending", done: false, current: false }
    ],
    ai_suggestions: {
      suggested_category: "Streetlights (99% confidence)",
      suggested_severity: "Urgent (High traffic intersection)",
      duplicate_flag: "Possible duplicate with traffic advisory alert"
    }
  }
];

// Demonstration Dashboard Metrics
const NAGARWATCH_MOCK_METRICS = {
  total: 248,
  pending: 42,
  in_progress: 31,
  resolved: 175,
  high_priority: 18
};

