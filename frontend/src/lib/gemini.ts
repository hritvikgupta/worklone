import { GoogleGenAI } from "@google/genai";

const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY || "" });

export async function generatePRD(featureName: string, description: string) {
  const response = await ai.models.generateContent({
    model: "gemini-3-flash-preview",
    contents: `Generate a short Product Requirements Document (PRD) for the following feature:
    Feature: ${featureName}
    Description: ${description}
    
    Include:
    1. Problem Statement
    2. User Stories
    3. Key Requirements
    4. Success Metrics`,
  });
  return response.text;
}

export async function prioritizeBacklog(tasks: string[]) {
  const response = await ai.models.generateContent({
    model: "gemini-3-flash-preview",
    contents: `Act as an expert Product Manager. Prioritize the following backlog items based on impact and effort. Return a JSON array of objects with 'id', 'title', 'priority' (high/medium/low), and 'reasoning'.
    Backlog: ${JSON.stringify(tasks)}`,
    config: {
      responseMimeType: "application/json",
    }
  });
  return JSON.parse(response.text || "[]");
}
